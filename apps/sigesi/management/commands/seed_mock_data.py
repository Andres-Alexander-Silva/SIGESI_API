"""Genera datos de prueba (mock) relacionalmente consistentes para SIGESI.

Crea registros a lo largo de todo el grafo de dominio (≥100 filas en total con
los valores por defecto) respetando los invariantes del modelo: códigos únicos,
``unique_together``, contraseñas vía ``set_password``, el blanqueo de ``email``
para egresados y el gate de aval (la mayoría de semilleros quedan ``aprobado``).

Uso:
    python manage.py seed_mock_data            # rellena hasta los conteos objetivo (idempotente)
    python manage.py seed_mock_data --flush    # borra los datos mock previos y vuelve a sembrar
    python manage.py seed_mock_data --scale 2  # duplica cada conteo por modelo
    python manage.py seed_mock_data --seed 42  # ejecución determinista (Faker + random)

Notas:
- Los usuarios sembrados llevan el prefijo de ``username`` ``mock_`` para que
  ``--flush`` los elimine sin tocar superusuarios ni cuentas reales.
- No toca la configuración RBAC (Menu / Opcion / Permiso): eso es configuración,
  no datos de prueba.
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.sigesi.models import (
    ProgramaAcademico, LineaInvestigacion, Indicador, Convocatoria,
    GrupoInvestigacion, Semillero, MatriculaSemillero,
    PlanEstrategico, PlanAccion, ObjetivosPlanAccion, Cronograma, ActividadCronograma,
    Proyecto, EvaluacionProyecto, FaseProyecto, HitoEntregable, Bitacora,
    Actividad, CronogramaProyecto, Evidencia, Alerta,
    CompetenciaInvestigativa, Rubrica, Evaluacion, PerfilInvestigativo,
    ProduccionAcademica, ParticipacionEvento,
    Postulacion, MedicionIndicador, Informe,
    User,
)

# Prefijo que marca a los usuarios sembrados (para flush selectivo).
MOCK_USER_PREFIX = 'mock_'
MOCK_PASSWORD = 'mock1234'

SEMESTRES = ['2024-1', '2024-2', '2025-1', '2025-2']

# Conteos objetivo por modelo (antes de aplicar --scale). Suman ~190 filas.
DEFAULT_TARGETS = {
    'programas': 4,
    'lineas': 5,
    'indicadores': 6,
    'convocatorias': 4,
    'usuarios': 20,
    'grupos': 4,
    'semilleros': 8,
    'matriculas': 12,
    'planes_estrategicos': 6,
    'planes_accion': 6,
    'cronogramas': 8,
    'actividades_cronograma': 16,
    'proyectos': 8,
    'evaluaciones_proyecto': 5,
    'hitos': 8,
    'bitacoras': 6,
    'actividades': 10,
    'cronogramas_proyecto': 8,
    'evidencias': 6,
    'alertas': 8,
    'competencias': 6,
    'rubricas': 6,
    'evaluaciones': 6,
    'producciones': 6,
    'participaciones': 5,
    'postulaciones': 5,
    'mediciones': 6,
    'informes': 5,
}

# Orden hoja→raíz para el borrado en --flush.
FLUSH_ORDER = [
    MedicionIndicador, Postulacion, ParticipacionEvento, ProduccionAcademica,
    Evaluacion, Rubrica, CompetenciaInvestigativa, PerfilInvestigativo,
    Informe, Alerta, Evidencia, CronogramaProyecto, Actividad, Bitacora,
    HitoEntregable, FaseProyecto, EvaluacionProyecto, Proyecto,
    ActividadCronograma, Cronograma, PlanAccion, PlanEstrategico, MatriculaSemillero,
    Semillero, GrupoInvestigacion, LineaInvestigacion, ProgramaAcademico,
    Indicador, Convocatoria,
]


class Command(BaseCommand):
    help = "Genera datos de prueba (mock) consistentes a lo largo del dominio de SIGESI."

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true',
                            help='Borra los datos mock previos antes de sembrar.')
        parser.add_argument('--scale', type=float, default=1.0,
                            help='Factor multiplicador sobre los conteos por defecto.')
        parser.add_argument('--seed', type=int, default=None,
                            help='Semilla para Faker/random (ejecución determinista).')

    # ------------------------------------------------------------------ run
    def handle(self, *args, **options):
        try:
            from faker import Faker
        except ImportError:
            self.stderr.write(self.style.ERROR(
                "Falta la dependencia 'Faker'. Instálala con: pip install Faker"))
            return

        seed = options['seed']
        self.fake = Faker('es_CO')
        if seed is not None:
            random.seed(seed)
            Faker.seed(seed)

        scale = options['scale']
        self.targets = {k: max(1, int(round(v * scale))) for k, v in DEFAULT_TARGETS.items()}
        self.created = {}

        with transaction.atomic():
            if options['flush']:
                self._flush()
            self._seed_all()

        total = sum(self.created.values())
        self.stdout.write("")
        for name in DEFAULT_TARGETS:
            self.stdout.write(f"  {name:24s}: +{self.created.get(name, 0)}")
        self.stdout.write(self.style.SUCCESS(
            f"\nSiembra completada. Filas creadas en esta ejecución: {total}."))

    # ----------------------------------------------------------------- flush
    def _flush(self):
        self.stdout.write("Borrando datos mock previos…")
        for model in FLUSH_ORDER:
            model.objects.all().delete()
        User.objects.filter(username__startswith=MOCK_USER_PREFIX).delete()

    # --------------------------------------------------------------- helpers
    def _topup(self, name, model, factory):
        """Crea filas hasta alcanzar el conteo objetivo (idempotente por conteo)."""
        target = self.targets[name]
        existing = model.objects.count()
        n = 0
        for i in range(existing, target):
            obj = factory(i)
            if obj is not None:
                n += 1
        self.created[name] = n

    @staticmethod
    def _rand_date(start_days_ago=400, span=380):
        base = date.today() - timedelta(days=random.randint(0, start_days_ago))
        return base + timedelta(days=random.randint(0, span))

    @staticmethod
    def _choice(text_choices):
        return random.choice([c[0] for c in text_choices.choices])

    # ------------------------------------------------------------- seed all
    def _seed_all(self):
        self._seed_catalogos()
        self._seed_usuarios()
        self._seed_organizacion()
        self._seed_planeacion()
        self._seed_proyectos()
        self._seed_seguimiento()
        self._seed_competencias()
        self._seed_produccion()
        self._seed_convocatorias_indicadores_informes()

    # ---- 1. catálogos sin FKs de dominio ----
    def _seed_catalogos(self):
        facultades = ['Facultad de Ingeniería', 'Facultad de Ciencias Básicas',
                      'Facultad de Educación', 'Facultad de Ciencias Empresariales']
        self._topup('programas', ProgramaAcademico, lambda i: ProgramaAcademico.objects.create(
            nombre=f"{self.fake.job()} (Programa {i + 1})"[:200],
            codigo=f"PRG{i + 1:03d}",
            facultad=random.choice(facultades),
        ))
        self._topup('lineas', LineaInvestigacion, lambda i: LineaInvestigacion.objects.create(
            nombre=f"Línea {self.fake.bs().title()}"[:200],
            descripcion=self.fake.paragraph(),
            mision=self.fake.sentence(),
            vision=self.fake.sentence(),
        ))
        self._topup('indicadores', Indicador, lambda i: Indicador.objects.create(
            nombre=f"Indicador {self.fake.word().title()} {i + 1}"[:200],
            descripcion=self.fake.sentence(),
            categoria=self._choice(Indicador.CategoriaChoices),
            formula="(numerador / denominador) * 100",
            meta=Decimal(random.randint(50, 100)),
            unidad_medida=random.choice(['%', 'unidades', 'puntos']),
        ))
        self._topup('convocatorias', Convocatoria, lambda i: Convocatoria.objects.create(
            titulo=f"Convocatoria {self.fake.catch_phrase()}"[:300],
            descripcion=self.fake.paragraph(),
            tipo=self._choice(Convocatoria.TipoChoices),
            entidad=self.fake.company(),
            fecha_apertura=self._rand_date(),
            fecha_cierre=self._rand_date(),
            requisitos=self.fake.paragraph(),
            presupuesto=Decimal(random.randint(1_000_000, 50_000_000)),
            url=self.fake.url(),
            estado=self._choice(Convocatoria.EstadoChoices),
        ))

    # ---- 2. usuarios ----
    def _seed_usuarios(self):
        # Distribución de roles dentro del objetivo de usuarios.
        target = self.targets['usuarios']
        roles_plan = (
            [['administrador']] * 2 +
            [['director_grupo']] * 3 +
            [['director_semillero']] * 4 +
            [['lider_estudiantil']] * 4 +
            [['estudiante']] * max(1, target - 13)
        )

        def factory(i):
            roles = roles_plan[i] if i < len(roles_plan) else ['estudiante']
            n = User.objects.count() + 1
            first = self.fake.first_name()
            last = self.fake.last_name()
            is_grad = 'estudiante' in roles and random.random() < 0.15
            user = User(
                username=f"{MOCK_USER_PREFIX}{n}",
                cedula=f"MK{n:08d}",
                first_name=first,
                last_name=last,
                correo_personal=f"mock{n}@example.com",
                email=f"mock{n}@ufps.edu.co",
                roles=roles,
                is_active=True,
                is_graduated=is_grad,
                telefono=self.fake.numerify('3#########'),
                codigo_estudiantil=(f"172{n:04d}" if 'estudiante' in roles else ''),
            )
            user.set_password(MOCK_PASSWORD)
            user.save()  # save() limpia email si is_graduated
            return user

        self._topup('usuarios', User, factory)

    # Pools por rol (incluye usuarios reales que tengan el rol).
    def _users_with(self, rol):
        pool = [u for u in User.objects.all() if u.tiene_rol(rol)]
        return pool

    # ---- 3. organización ----
    def _seed_organizacion(self):
        programas = list(ProgramaAcademico.objects.all())
        lineas = list(LineaInvestigacion.objects.all())
        dir_grupo = self._users_with('director_grupo') or self._users_with('administrador')
        dir_sem = self._users_with('director_semillero') or dir_grupo
        lideres = self._users_with('lider_estudiantil') or self._users_with('estudiante')
        admins = self._users_with('administrador')
        estudiantes = self._users_with('estudiante')

        def grupo_factory(i):
            g = GrupoInvestigacion.objects.create(
                nombre=f"Grupo {self.fake.color_name()} {i + 1}"[:200],
                codigo=f"GRP{i + 1:03d}",
                descripcion=self.fake.paragraph(),
                fecha_creacion=self._rand_date(),
                programa_academico=random.choice(programas),
                director=random.choice(dir_grupo) if dir_grupo else None,
            )
            if lineas:
                g.lineas_investigacion.set(random.sample(lineas, k=min(2, len(lineas))))
            return g
        self._topup('grupos', GrupoInvestigacion, grupo_factory)

        grupos = list(GrupoInvestigacion.objects.all())

        def semillero_factory(i):
            aprobado = random.random() < 0.75
            s = Semillero.objects.create(
                nombre=f"Semillero {self.fake.word().title()} {i + 1}"[:200],
                codigo=f"SEM{i + 1:03d}",
                objetivo=self.fake.paragraph(),
                mision=self.fake.sentence(),
                vision=self.fake.sentence(),
                fecha_creacion=self._rand_date(),
                grupo_investigacion=random.choice(grupos),
                director=random.choice(dir_sem) if dir_sem else None,
                lider_estudiantil=random.choice(lideres) if lideres else None,
                estado_aval=(Semillero.EstadoAvalChoices.APROBADO if aprobado
                             else self._choice(Semillero.EstadoAvalChoices)),
            )
            if aprobado:
                s.tipo_documento = self._choice(Semillero.TipoDocumentoChoices)
                s.numero_acta = self.fake.numerify('ACTA-####')
                s.fecha_aprobacion = self._rand_date()
                s.usuario_aprobacion = random.choice(admins) if admins else None
                s.save()
            if lineas:
                s.lineas_investigacion.set(random.sample(lineas, k=min(2, len(lineas))))
            return s
        self._topup('semilleros', Semillero, semillero_factory)

        semilleros = list(Semillero.objects.all())

        # Matrículas: combinaciones únicas (estudiante, semillero, semestre).
        combos = [(e, s, sem) for e in estudiantes for s in semilleros for sem in SEMESTRES]
        random.shuffle(combos)
        it = iter(combos)

        def matricula_factory(i):
            try:
                e, s, sem = next(it)
            except StopIteration:
                return None
            obj, _ = MatriculaSemillero.objects.get_or_create(
                estudiante=e, semillero=s, semestre=sem,
                defaults={'estado': self._choice(MatriculaSemillero.EstadoChoices)},
            )
            return obj
        self._topup('matriculas', MatriculaSemillero, matricula_factory)

    # ---- 4. planeación ----
    def _seed_planeacion(self):
        semilleros = list(Semillero.objects.all())
        admins = self._users_with('administrador')
        responsables = (self._users_with('director_semillero')
                        or self._users_with('lider_estudiantil') or list(User.objects.all()))

        anios = [2023, 2024, 2025, 2026]
        pe_combos = [(s, a) for s in semilleros for a in anios]
        random.shuffle(pe_combos)
        pe_it = iter(pe_combos)

        def pe_factory(i):
            try:
                s, anio = next(pe_it)
            except StopIteration:
                return None
            obj, _ = PlanEstrategico.objects.get_or_create(
                semillero=s, anio=anio,
                defaults=dict(
                    titulo=f"Plan estratégico {anio} — {s.nombre}"[:300],
                    objetivos=self.fake.paragraph(),
                    metas=self.fake.paragraph(),
                    indicadores=self.fake.paragraph(),
                    estado=self._choice(PlanEstrategico.EstadoChoices),
                ),
            )
            return obj
        self._topup('planes_estrategicos', PlanEstrategico, pe_factory)

        pa_combos = [(s, sem) for s in semilleros for sem in SEMESTRES]
        random.shuffle(pa_combos)
        pa_it = iter(pa_combos)

        def pa_factory(i):
            try:
                s, sem = next(pa_it)
            except StopIteration:
                return None
            pe = s.planes_estrategicos.first()
            obj, _ = PlanAccion.objects.get_or_create(
                semillero=s, semestre=sem,
                defaults=dict(
                    plan_estrategico=pe,
                    titulo=f"Plan de acción {sem} — {s.nombre}"[:300],
                    metas=self.fake.paragraph(),
                    estado=self._choice(PlanAccion.EstadoChoices),
                    aprobado_por=random.choice(admins) if admins else None,
                ),
            )
            return obj
        self._topup('planes_accion', PlanAccion, pa_factory)

        planes_accion = list(PlanAccion.objects.all())

        # Objetivos de cada plan de acción (2-4 por plan). Idempotente: solo
        # crea para los planes que aún no tienen objetivos.
        nuevos_objetivos = []
        for pa in planes_accion:
            if pa.objetivos.exists():
                continue
            nuevos_objetivos.extend([
                ObjetivosPlanAccion(
                    plan_accion=pa,
                    descripcion=self.fake.sentence(),
                    categoria=self._choice(ObjetivosPlanAccion.CategoriaChoices),
                )
                for _ in range(random.randint(2, 4))
            ])
        if nuevos_objetivos:
            ObjetivosPlanAccion.objects.bulk_create(nuevos_objetivos)

        def cron_factory(i):
            if not planes_accion:
                return None
            ini = self._rand_date()
            return Cronograma.objects.create(
                plan_accion=random.choice(planes_accion),
                descripcion=self.fake.paragraph(),
                responsable=random.choice(responsables) if responsables else None,
                fecha_inicio=ini,
                fecha_fin=ini + timedelta(days=random.randint(15, 120)),
                cumplido=random.choice([True, False]),
            )
        self._topup('cronogramas', Cronograma, cron_factory)

        cronogramas = list(Cronograma.objects.all())

        def actcron_factory(i):
            if not cronogramas:
                return None
            ini = self._rand_date()
            fin_estimada = ini + timedelta(days=random.randint(15, 120))
            cumplida = random.choice([True, False])
            return ActividadCronograma.objects.create(
                cronograma=random.choice(cronogramas),
                titulo=self.fake.sentence(nb_words=5)[:300],
                descripcion=self.fake.paragraph(),
                responsable=random.choice(responsables) if responsables else None,
                objetivo_general=self.fake.sentence(),
                objetivos_especificos=self.fake.paragraph(),
                fecha_inicio=ini,
                fecha_fin_estimada=fin_estimada,
                fecha_fin=fin_estimada if cumplida else None,
            )
        self._topup('actividades_cronograma', ActividadCronograma, actcron_factory)

    # ---- 5. proyectos ----
    def _seed_proyectos(self):
        # Proyectos colgados de semilleros aprobados (para que el gate de aval pase).
        sem_aprobados = list(Semillero.objects.filter(
            estado_aval=Semillero.EstadoAvalChoices.APROBADO))
        if not sem_aprobados:
            sem_aprobados = list(Semillero.objects.all())
        lineas = list(LineaInvestigacion.objects.all())
        directores = (self._users_with('director_semillero')
                      or self._users_with('director_grupo') or list(User.objects.all()))
        lideres = self._users_with('lider_estudiantil') or self._users_with('estudiante')
        estudiantes = self._users_with('estudiante') or list(User.objects.all())

        def proyecto_factory(i):
            p = Proyecto.objects.create(
                titulo=f"Proyecto {self.fake.catch_phrase()}"[:300],
                codigo=f"PROY{i + 1:03d}",
                descripcion=self.fake.paragraph(),
                objetivo_general=self.fake.paragraph(),
                objetivos_especificos=self.fake.paragraph(),
                linea_investigacion=random.choice(lineas) if lineas else None,
                director=random.choice(directores) if directores else None,
                lider=random.choice(lideres) if lideres else None,
                estado=self._choice(Proyecto.EstadoChoices),
                fecha_inicio=self._rand_date(),
                fecha_fin_estimada=self._rand_date(start_days_ago=0, span=365),
            )
            p.semilleros.set(random.sample(sem_aprobados, k=min(2, len(sem_aprobados))))
            if estudiantes:
                p.estudiantes.set(random.sample(estudiantes, k=min(3, len(estudiantes))))
            return p
        self._topup('proyectos', Proyecto, proyecto_factory)

        proyectos = list(Proyecto.objects.all())
        evaluadores = directores

        def eval_factory(i):
            if not proyectos:
                return None
            p = random.choice(proyectos)
            return EvaluacionProyecto.objects.create(
                proyecto=p,
                evaluador=random.choice(evaluadores) if evaluadores else None,
                calificacion=Decimal(f"{random.uniform(1.0, 5.0):.1f}"),
                estado_proyecto=self._choice(Proyecto.EstadoChoices),
                observaciones=self.fake.paragraph(),
                recomendaciones=self.fake.sentence(),
            )
        self._topup('evaluaciones_proyecto', EvaluacionProyecto, eval_factory)

        # Fases: combinaciones únicas (proyecto, fase).
        fase_combos = [(p, f[0]) for p in proyectos for f in FaseProyecto.FaseChoices.choices]
        fase_it = iter(fase_combos)

        def fase_factory(i):
            try:
                p, fase = next(fase_it)
            except StopIteration:
                return None
            ini = self._rand_date()
            obj, _ = FaseProyecto.objects.get_or_create(
                proyecto=p, fase=fase,
                defaults=dict(
                    descripcion=self.fake.sentence(),
                    orden=i + 1,
                    estado=self._choice(FaseProyecto.EstadoChoices),
                    fecha_inicio=ini,
                    fecha_fin=ini + timedelta(days=random.randint(20, 90)),
                ),
            )
            return obj
        self._topup_fases(fase_factory)

    def _topup_fases(self, factory):
        # Las fases no tienen target propio; se generan ~1.5 por proyecto.
        target = max(self.targets['hitos'], FaseProyecto.objects.count() + len(list(Proyecto.objects.all())))
        existing = FaseProyecto.objects.count()
        n = 0
        for i in range(existing, target):
            if factory(i) is not None:
                n += 1
        self.created['fases'] = n

    # ---- 6. seguimiento (hitos, bitácoras, actividades, cronograma, evidencias, alertas) ----
    def _seed_seguimiento(self):
        proyectos = list(Proyecto.objects.all())
        fases = list(FaseProyecto.objects.all())
        responsables = list(User.objects.all())

        def hito_factory(i):
            if not fases:
                return None
            return HitoEntregable.objects.create(
                fase=random.choice(fases),
                tipo=self._choice(HitoEntregable.TipoChoices),
                titulo=self.fake.sentence(nb_words=4)[:300],
                descripcion=self.fake.sentence(),
                fecha_limite=self._rand_date(start_days_ago=0, span=200),
                estado=self._choice(HitoEntregable.EstadoChoices),
                responsable=random.choice(responsables) if responsables else None,
            )
        self._topup('hitos', HitoEntregable, hito_factory)

        def bitacora_factory(i):
            if not proyectos:
                return None
            return Bitacora.objects.create(
                proyecto=random.choice(proyectos),
                tipo=self._choice(Bitacora.TipoChoices),
                titulo=self.fake.sentence(nb_words=5)[:300],
                descripcion=self.fake.paragraph(),
                fecha=self._rand_date(),
                autor=random.choice(responsables) if responsables else None,
            )
        self._topup('bitacoras', Bitacora, bitacora_factory)

        def actividad_factory(i):
            if not proyectos:
                return None
            ini = self._rand_date()
            return Actividad.objects.create(
                proyecto=random.choice(proyectos),
                titulo=self.fake.sentence(nb_words=5)[:300],
                descripcion=self.fake.paragraph(),
                responsable=random.choice(responsables) if responsables else None,
                fecha_inicio=ini,
                fecha_fin=ini + timedelta(days=random.randint(7, 90)),
                estado=self._choice(Actividad.EstadoChoices),
                porcentaje_avance=random.randint(0, 100),
            )
        self._topup('actividades', Actividad, actividad_factory)

        def cronproy_factory(i):
            if not proyectos:
                return None
            ini = self._rand_date()
            return CronogramaProyecto.objects.create(
                proyecto=random.choice(proyectos),
                actividad=self.fake.sentence(nb_words=4)[:300],
                descripcion_actividad=self.fake.paragraph(),
                fecha_inicio=ini,
                fecha_fin=ini + timedelta(days=random.randint(10, 60)),
                fecha_entrega=ini + timedelta(days=random.randint(60, 90)),
                estado_actividad=self._choice(CronogramaProyecto.EstadoChoices),
                observaciones=self.fake.sentence(),
            )
        self._topup('cronogramas_proyecto', CronogramaProyecto, cronproy_factory)

        actividades = list(Actividad.objects.all())

        def evidencia_factory(i):
            if not actividades:
                return None
            return Evidencia.objects.create(
                actividad=random.choice(actividades),
                tipo=self._choice(Evidencia.TipoChoices),
                titulo=self.fake.sentence(nb_words=4)[:300],
                descripcion=self.fake.sentence(),
                archivo=f"evidencias/mock/evidencia_{i + 1}.pdf",  # placeholder, sin archivo real
                subido_por=random.choice(responsables) if responsables else None,
            )
        self._topup('evidencias', Evidencia, evidencia_factory)

        def alerta_factory(i):
            if not responsables:
                return None
            p = random.choice(proyectos) if proyectos else None
            return Alerta.objects.create(
                tipo=self._choice(Alerta.TipoChoices),
                prioridad=self._choice(Alerta.PrioridadChoices),
                titulo=self.fake.sentence(nb_words=5)[:300],
                mensaje=self.fake.paragraph(),
                proyecto=p,
                actividad=(p.actividades.first() if p else None),
                destinatario=random.choice(responsables),
                leida=random.choice([True, False]),
            )
        self._topup('alertas', Alerta, alerta_factory)

    # ---- 7. competencias ----
    def _seed_competencias(self):
        semilleros = list(Semillero.objects.all())
        estudiantes = self._users_with('estudiante') or list(User.objects.all())
        evaluadores = (self._users_with('director_semillero')
                       or self._users_with('director_grupo') or list(User.objects.all()))

        def comp_factory(i):
            if not semilleros:
                return None
            return CompetenciaInvestigativa.objects.create(
                nombre=f"Competencia {self.fake.word().title()} {i + 1}"[:200],
                descripcion=self.fake.paragraph(),
                nivel=self._choice(CompetenciaInvestigativa.NivelChoices),
                indicadores=self.fake.paragraph(),
                semillero=random.choice(semilleros),
            )
        self._topup('competencias', CompetenciaInvestigativa, comp_factory)

        competencias = list(CompetenciaInvestigativa.objects.all())

        def rubrica_factory(i):
            if not competencias:
                return None
            return Rubrica.objects.create(
                competencia=random.choice(competencias),
                criterio=self.fake.sentence(nb_words=4)[:300],
                descripcion_basico=self.fake.sentence(),
                descripcion_intermedio=self.fake.sentence(),
                descripcion_avanzado=self.fake.sentence(),
                peso=Decimal(f"{random.uniform(0.5, 3.0):.2f}"),
            )
        self._topup('rubricas', Rubrica, rubrica_factory)

        def evaluacion_factory(i):
            if not competencias or not estudiantes:
                return None
            return Evaluacion.objects.create(
                estudiante=random.choice(estudiantes),
                evaluador=random.choice(evaluadores) if evaluadores else None,
                competencia=random.choice(competencias),
                tipo=self._choice(Evaluacion.TipoChoices),
                nivel_alcanzado=self._choice(Evaluacion.NivelAlcanzadoChoices),
                puntaje=Decimal(f"{random.uniform(1.0, 5.0):.2f}"),
                observaciones=self.fake.sentence(),
                semestre=random.choice(SEMESTRES),
            )
        self._topup('evaluaciones', Evaluacion, evaluacion_factory)

        # Perfil investigativo: OneToOne, uno por estudiante sin perfil.
        sin_perfil = [e for e in estudiantes
                      if not PerfilInvestigativo.objects.filter(estudiante=e).exists()]
        n = 0
        for e in sin_perfil:
            PerfilInvestigativo.objects.create(
                estudiante=e,
                resumen=self.fake.paragraph(),
                fortalezas=self.fake.sentence(),
                areas_mejora=self.fake.sentence(),
            )
            n += 1
        self.created['perfiles'] = n

    # ---- 8. producción y eventos ----
    def _seed_produccion(self):
        semilleros = list(Semillero.objects.all())
        proyectos = list(Proyecto.objects.all())
        lineas = list(LineaInvestigacion.objects.all())
        autores_pool = self._users_with('estudiante') or list(User.objects.all())
        participantes = list(User.objects.all())

        def prod_factory(i):
            if not semilleros:
                return None
            p = ProduccionAcademica.objects.create(
                titulo=f"{self.fake.sentence(nb_words=6)}"[:500],
                tipo=self._choice(ProduccionAcademica.TipoChoices),
                descripcion=self.fake.paragraph(),
                proyecto=random.choice(proyectos) if proyectos else None,
                semillero=random.choice(semilleros),
                linea_investigacion=random.choice(lineas) if lineas else None,
                doi=self.fake.numerify('10.####/mock.####'),
                url_repositorio=self.fake.url(),
                revista_evento=self.fake.company(),
                fecha_publicacion=self._rand_date(),
                estado=self._choice(ProduccionAcademica.EstadoChoices),
            )
            if autores_pool:
                p.autores.set(random.sample(autores_pool, k=min(2, len(autores_pool))))
            return p
        self._topup('producciones', ProduccionAcademica, prod_factory)

        producciones = list(ProduccionAcademica.objects.all())

        def part_factory(i):
            if not participantes:
                return None
            ini = self._rand_date()
            return ParticipacionEvento.objects.create(
                produccion=random.choice(producciones) if producciones else None,
                evento=f"Evento {self.fake.catch_phrase()}"[:300],
                lugar=self.fake.city(),
                fecha_inicio=ini,
                fecha_fin=ini + timedelta(days=random.randint(1, 5)),
                tipo_participacion=self._choice(ParticipacionEvento.TipoParticipacionChoices),
                participante=random.choice(participantes),
            )
        self._topup('participaciones', ParticipacionEvento, part_factory)

    # ---- 9. postulaciones, mediciones, informes ----
    def _seed_convocatorias_indicadores_informes(self):
        convocatorias = list(Convocatoria.objects.all())
        semilleros = list(Semillero.objects.all())
        proyectos = list(Proyecto.objects.all())
        estudiantes = self._users_with('estudiante') or list(User.objects.all())
        indicadores = list(Indicador.objects.all())
        registradores = list(User.objects.all())

        def post_factory(i):
            if not convocatorias or not semilleros:
                return None
            p = Postulacion.objects.create(
                convocatoria=random.choice(convocatorias),
                semillero=random.choice(semilleros),
                proyecto=random.choice(proyectos) if proyectos else None,
                estado=self._choice(Postulacion.EstadoChoices),
                observaciones=self.fake.sentence(),
                resultado=self.fake.sentence(),
            )
            if estudiantes:
                p.estudiantes.set(random.sample(estudiantes, k=min(2, len(estudiantes))))
            return p
        self._topup('postulaciones', Postulacion, post_factory)

        # Mediciones: combinaciones únicas (indicador, semillero, semestre).
        med_combos = [(ind, s, sem) for ind in indicadores for s in semilleros for sem in SEMESTRES]
        random.shuffle(med_combos)
        med_it = iter(med_combos)

        def med_factory(i):
            try:
                ind, s, sem = next(med_it)
            except StopIteration:
                return None
            obj, _ = MedicionIndicador.objects.get_or_create(
                indicador=ind, semillero=s, semestre=sem,
                defaults=dict(
                    valor=Decimal(f"{random.uniform(0, 100):.2f}"),
                    observaciones=self.fake.sentence(),
                    registrado_por=random.choice(registradores) if registradores else None,
                ),
            )
            return obj
        self._topup('mediciones', MedicionIndicador, med_factory)

        def informe_factory(i):
            if not semilleros:
                return None
            return Informe.objects.create(
                semillero=random.choice(semilleros),
                titulo=f"Informe {self.fake.catch_phrase()}"[:300],
                tipo=self._choice(Informe.TipoChoices),
                semestre=random.choice(SEMESTRES),
                contenido=self.fake.paragraph(),
                estado=self._choice(Informe.EstadoChoices),
                generado_por=random.choice(registradores) if registradores else None,
            )
        self._topup('informes', Informe, informe_factory)
