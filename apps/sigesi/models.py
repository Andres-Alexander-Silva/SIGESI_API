from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.conf import settings


# ============================================================
# SISTEMA DE PERMISOS: MENÚS, OPCIONES Y PERMISOS POR ROL
# ============================================================

class Menu(models.Model):
    """Menú principal del sistema."""

    nombre = models.CharField(max_length=100, unique=True)
    icono  = models.CharField(max_length=50, unique=True)
    estado = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'menus'


class Opcion(models.Model):
    """Opción de navegación dentro de un menú."""

    menu   = models.ForeignKey(Menu, null=False, on_delete=models.RESTRICT, related_name='opciones')
    nombre = models.CharField(max_length=100)
    url    = models.CharField(max_length=100, unique=True)
    estado = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'opciones'


class Permiso(models.Model):
    """Permisos CRUD de un rol sobre una opción."""

    rol = models.CharField(
        max_length=30,
        choices=[
            ('administrador',       'Administrador'),
            ('director_grupo',      'Director de Grupo'),
            ('director_semillero',  'Director de Semillero'),
            ('lider_estudiantil',   'Líder Estudiantil'),
            ('estudiante',          'Estudiante'),
        ],
    )
    opcion           = models.ForeignKey(Opcion, null=False, on_delete=models.RESTRICT, related_name='permisos')
    puede_consultar  = models.BooleanField(default=False)
    puede_crear      = models.BooleanField(default=False)
    puede_actualizar = models.BooleanField(default=False)
    puede_eliminar   = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_rol_display()} -> {self.opcion}"

    class Meta:
        db_table       = 'permisos'
        unique_together = ['rol', 'opcion']
        ordering        = ['rol', 'opcion']


# ============================================================
# USUARIOS
# ============================================================

class User(AbstractUser):
    """Modelo de usuario personalizado del sistema."""

    class RolChoices(models.TextChoices):
        ADMINISTRADOR = 'administrador', 'Administrador'
        DIRECTOR_GRUPO = 'director_grupo', 'Director de Grupo'
        DIRECTOR_SEMILLERO = 'director_semillero', 'Director de Semillero'
        LIDER_ESTUDIANTIL = 'lider_estudiantil', 'Líder Estudiantil'
        ESTUDIANTE = 'estudiante', 'Estudiante'

    cedula = models.CharField(
        max_length=20, unique=True, verbose_name='Cédula')
    telefono = models.CharField(
        max_length=20, blank=True, verbose_name='Teléfono')
    foto = models.ImageField(upload_to='usuarios/fotos/',
                             blank=True, null=True, verbose_name='Foto de perfil')
    roles = ArrayField(
        models.CharField(max_length=30, choices=RolChoices.choices),
        default=list,
        verbose_name='Roles',
        help_text='Lista de roles asignados al usuario.',
    )
    codigo_estudiantil = models.CharField(
        max_length=20, blank=True, verbose_name='Código estudiantil')
    programa_academico = models.ForeignKey(
        'ProgramaAcademico',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios',
        verbose_name='Programa académico'
    )
    correo_personal = models.EmailField(
        unique=True, verbose_name='Correo Personal')
    is_graduated = models.BooleanField(
        default=False, verbose_name='Es egresado')
    email = models.EmailField(
        unique=True, blank=True, null=True, verbose_name='Email institucional')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.get_full_name()} - {', '.join(self.get_roles_display())}"

    def save(self, *args, **kwargs):
        if self.is_graduated:
            self.email = None
        super().save(*args, **kwargs)

    # ---- Helpers multi-rol ----

    def tiene_rol(self, rol):
        """Verifica si el usuario tiene un rol específico."""
        return rol in self.roles

    def tiene_alguno_de(self, roles_lista):
        """Verifica si el usuario tiene al menos uno de los roles dados."""
        return bool(set(self.roles) & set(roles_lista))

    def get_roles_display(self):
        """Retorna la representación legible de todos los roles."""
        display_map = dict(self.RolChoices.choices)
        return [display_map.get(r, r) for r in self.roles]

    def puede_consultar(self, url_opcion):
        """Verifica si el usuario puede consultar la opción con la URL dada."""
        return Permiso.objects.filter(
            rol__in=self.roles, opcion__url=url_opcion,
            puede_consultar=True, opcion__estado=True,
        ).exists()

    def obtener_menus(self):
        """Retorna los menús accesibles según los roles del usuario."""
        return Menu.objects.filter(
            estado=True,
            opciones__estado=True,
            opciones__permisos__rol__in=self.roles,
        ).distinct()


# ============================================================
# ESTRUCTURA ORGANIZATIVA
# ============================================================

class ProgramaAcademico(models.Model):
    """Unidad académica a la cual están adscritos los grupos de investigación."""

    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    codigo = models.CharField(
        max_length=20, unique=True, verbose_name='Código')
    facultad = models.CharField(max_length=200, verbose_name='Facultad')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Programa Académico'
        verbose_name_plural = 'Programas Académicos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class LineaInvestigacion(models.Model):
    """Eje temático que orienta la actividad investigativa."""

    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Línea de Investigación'
        verbose_name_plural = 'Líneas de Investigación'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class GrupoInvestigacion(models.Model):
    """Entidad formal que agrupa semilleros, líneas y docentes investigadores."""

    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    codigo = models.CharField(
        max_length=20, unique=True, verbose_name='Código')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    fecha_creacion = models.DateField(verbose_name='Fecha de creación')
    programa_academico = models.ForeignKey(
        ProgramaAcademico,
        on_delete=models.CASCADE,
        related_name='grupos_investigacion',
        verbose_name='Programa académico'
    )
    director = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='grupos_dirigidos',
        verbose_name='Director'
    )
    lineas_investigacion = models.ManyToManyField(
        LineaInvestigacion,
        related_name='grupos',
        blank=True,
        verbose_name='Líneas de investigación'
    )
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Grupo de Investigación'
        verbose_name_plural = 'Grupos de Investigación'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Semillero(models.Model):
    """Espacio formativo que agrupa estudiantes bajo la dirección de un docente."""

    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    codigo = models.CharField(
        max_length=20, unique=True, verbose_name='Código')
    objetivo = models.TextField(verbose_name='Objetivo')
    mision = models.TextField(blank=True, verbose_name='Misión')
    vision = models.TextField(blank=True, verbose_name='Visión')
    fecha_creacion = models.DateField(verbose_name='Fecha de creación')
    grupo_investigacion = models.ForeignKey(
        GrupoInvestigacion,
        on_delete=models.CASCADE,
        related_name='semilleros',
        verbose_name='Grupo de investigación'
    )
    director = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='semilleros_dirigidos',
        verbose_name='Director de semillero'
    )
    lider_estudiantil = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='semilleros_liderados',
        verbose_name='Líder estudiantil'
    )
    lineas_investigacion = models.ManyToManyField(
        LineaInvestigacion,
        related_name='semilleros',
        blank=True,
        verbose_name='Líneas de investigación'
    )
    logo = models.ImageField(
        upload_to='semilleros/logos/', blank=True, null=True, verbose_name='Logo')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Semillero'
        verbose_name_plural = 'Semilleros'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class MatriculaSemillero(models.Model):
    """Registro de inscripción de un estudiante en un semillero por semestre."""

    class EstadoChoices(models.TextChoices):
        ACTIVA = 'activa', 'Activa'
        INACTIVA = 'inactiva', 'Inactiva'
        RETIRADO = 'retirado', 'Retirado'

    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matriculas_semillero',
        verbose_name='Estudiante'
    )
    semillero = models.ForeignKey(
        Semillero,
        on_delete=models.CASCADE,
        related_name='matriculas',
        verbose_name='Semillero'
    )
    semestre = models.CharField(
        max_length=10, verbose_name='Semestre (ej: 2025-1)')
    fecha_inscripcion = models.DateField(
        auto_now_add=True, verbose_name='Fecha de inscripción')
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.ACTIVA,
        verbose_name='Estado'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Matrícula de Semillero'
        verbose_name_plural = 'Matrículas de Semillero'
        unique_together = ['estudiante', 'semillero', 'semestre']
        ordering = ['-semestre']

    def __str__(self):
        return f"{self.estudiante} - {self.semillero} ({self.semestre})"


# ============================================================
# PLANEACIÓN ESTRATÉGICA Y OPERATIVA
# ============================================================

class PlanEstrategico(models.Model):
    """Plan del semillero con objetivos anuales, metas, indicadores y estado."""

    class EstadoChoices(models.TextChoices):
        BORRADOR = 'borrador', 'Borrador'
        EN_REVISION = 'en_revision', 'En Revisión'
        APROBADO = 'aprobado', 'Aprobado'
        EN_EJECUCION = 'en_ejecucion', 'En Ejecución'
        FINALIZADO = 'finalizado', 'Finalizado'

    semillero = models.ForeignKey(
        Semillero,
        on_delete=models.CASCADE,
        related_name='planes_estrategicos',
        verbose_name='Semillero'
    )
    titulo = models.CharField(max_length=300, verbose_name='Título')
    anio = models.PositiveIntegerField(verbose_name='Año')
    objetivos = models.TextField(verbose_name='Objetivos')
    metas = models.TextField(verbose_name='Metas')
    indicadores = models.TextField(verbose_name='Indicadores')
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.BORRADOR,
        verbose_name='Estado'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Plan Estratégico'
        verbose_name_plural = 'Planes Estratégicos'
        unique_together = ['semillero', 'anio']
        ordering = ['-anio']

    def __str__(self):
        return f"{self.titulo} - {self.semillero} ({self.anio})"


class PlanAccion(models.Model):
    """Documento semestral con actividades, metas, responsables y cronograma."""

    class EstadoChoices(models.TextChoices):
        BORRADOR = 'borrador', 'Borrador'
        ENVIADO = 'enviado', 'Enviado'
        APROBADO = 'aprobado', 'Aprobado'
        RECHAZADO = 'rechazado', 'Rechazado'
        EN_EJECUCION = 'en_ejecucion', 'En Ejecución'
        FINALIZADO = 'finalizado', 'Finalizado'

    semillero = models.ForeignKey(
        Semillero,
        on_delete=models.CASCADE,
        related_name='planes_accion',
        verbose_name='Semillero'
    )
    plan_estrategico = models.ForeignKey(
        PlanEstrategico,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planes_accion',
        verbose_name='Plan estratégico'
    )
    titulo = models.CharField(max_length=300, verbose_name='Título')
    semestre = models.CharField(
        max_length=10, verbose_name='Semestre (ej: 2025-1)')
    objetivos = models.TextField(verbose_name='Objetivos')
    metas = models.TextField(verbose_name='Metas')
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.BORRADOR,
        verbose_name='Estado'
    )
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planes_aprobados',
        verbose_name='Aprobado por'
    )
    fecha_aprobacion = models.DateTimeField(
        null=True, blank=True, verbose_name='Fecha de aprobación')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Plan de Acción'
        verbose_name_plural = 'Planes de Acción'
        unique_together = ['semillero', 'semestre']
        ordering = ['-semestre']

    def __str__(self):
        return f"{self.titulo} - {self.semillero} ({self.semestre})"


class Cronograma(models.Model):
    """Planificación semestral detallada de actividades con fechas y responsables."""

    plan_accion = models.ForeignKey(
        PlanAccion,
        on_delete=models.CASCADE,
        related_name='cronogramas',
        verbose_name='Plan de acción'
    )
    actividad = models.CharField(max_length=300, verbose_name='Actividad')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cronogramas_asignados',
        verbose_name='Responsable'
    )
    fecha_inicio = models.DateField(verbose_name='Fecha de inicio')
    fecha_fin = models.DateField(verbose_name='Fecha de fin')
    cumplido = models.BooleanField(default=False, verbose_name='Cumplido')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cronograma'
        verbose_name_plural = 'Cronogramas'
        ordering = ['fecha_inicio']

    def __str__(self):
        return f"{self.actividad} ({self.fecha_inicio} - {self.fecha_fin})"


# ============================================================
# PROYECTOS Y SEGUIMIENTO
# ============================================================

class Proyecto(models.Model):
    """Iniciativa de investigación con fases definidas y resultados esperados."""

    class EstadoChoices(models.TextChoices):
        IDEA = 'idea', 'Idea'
        PROPUESTA = 'propuesta', 'Propuesta'
        EN_EJECUCION = 'en_ejecucion', 'En Ejecución'
        EN_RESULTADOS = 'en_resultados', 'En Resultados'
        CERRADO = 'cerrado', 'Cerrado'
        CANCELADO = 'cancelado', 'Cancelado'

    titulo = models.CharField(max_length=300, verbose_name='Título')
    codigo = models.CharField(
        max_length=20, unique=True, verbose_name='Código')
    descripcion = models.TextField(verbose_name='Descripción')
    objetivo_general = models.TextField(verbose_name='Objetivo general')
    objetivos_especificos = models.TextField(
        blank=True, verbose_name='Objetivos específicos')
    semilleros = models.ManyToManyField(
        Semillero,
        related_name='proyectos',
        verbose_name='Semilleros'
    )
    linea_investigacion = models.ForeignKey(
        LineaInvestigacion,
        on_delete=models.SET_NULL,
        null=True,
        related_name='proyectos',
        verbose_name='Línea de investigación'
    )
    director = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='proyectos_dirigidos',
        verbose_name='Director del proyecto'
    )
    lider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proyectos_liderados',
        verbose_name='Líder estudiantil'
    )
    estudiantes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='proyectos_vinculados',
        blank=True,
        verbose_name='Estudiantes vinculados'
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.IDEA,
        verbose_name='Estado'
    )
    fecha_inicio = models.DateField(
        null=True, blank=True, verbose_name='Fecha de inicio')
    fecha_fin_estimada = models.DateField(
        null=True, blank=True, verbose_name='Fecha fin estimada')
    fecha_cierre = models.DateField(
        null=True, blank=True, verbose_name='Fecha de cierre')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        ordering = ['-created_at']

    def __str__(self):
        return self.titulo


class FaseProyecto(models.Model):
    """Etapa del ciclo de vida del proyecto."""

    class FaseChoices(models.TextChoices):
        IDEA = 'idea', 'Idea'
        PROPUESTA = 'propuesta', 'Propuesta'
        EJECUCION = 'ejecucion', 'Ejecución'
        RESULTADOS = 'resultados', 'Resultados'
        CIERRE = 'cierre', 'Cierre'

    class EstadoChoices(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        EN_PROGRESO = 'en_progreso', 'En Progreso'
        COMPLETADA = 'completada', 'Completada'

    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name='fases',
        verbose_name='Proyecto'
    )
    fase = models.CharField(
        max_length=20, choices=FaseChoices.choices, verbose_name='Fase')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    orden = models.PositiveIntegerField(default=1, verbose_name='Orden')
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.PENDIENTE,
        verbose_name='Estado'
    )
    fecha_inicio = models.DateField(
        null=True, blank=True, verbose_name='Fecha de inicio')
    fecha_fin = models.DateField(
        null=True, blank=True, verbose_name='Fecha de fin')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Fase del Proyecto'
        verbose_name_plural = 'Fases del Proyecto'
        ordering = ['orden']
        unique_together = ['proyecto', 'fase']

    def __str__(self):
        return f"{self.proyecto.titulo} - {self.get_fase_display()}"


class HitoEntregable(models.Model):
    """Punto de control o producto esperado en cada fase del proyecto."""

    class TipoChoices(models.TextChoices):
        HITO = 'hito', 'Hito'
        ENTREGABLE = 'entregable', 'Entregable'

    class EstadoChoices(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        EN_PROGRESO = 'en_progreso', 'En Progreso'
        COMPLETADO = 'completado', 'Completado'
        ATRASADO = 'atrasado', 'Atrasado'

    fase = models.ForeignKey(
        FaseProyecto,
        on_delete=models.CASCADE,
        related_name='hitos_entregables',
        verbose_name='Fase'
    )
    tipo = models.CharField(
        max_length=20, choices=TipoChoices.choices, verbose_name='Tipo')
    titulo = models.CharField(max_length=300, verbose_name='Título')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    fecha_limite = models.DateField(verbose_name='Fecha límite')
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.PENDIENTE,
        verbose_name='Estado'
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hitos_asignados',
        verbose_name='Responsable'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Hito / Entregable'
        verbose_name_plural = 'Hitos / Entregables'
        ordering = ['fecha_limite']

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.titulo}"


class Bitacora(models.Model):
    """Registro cronológico de actividades, decisiones y cambios de un proyecto."""

    class TipoChoices(models.TextChoices):
        ACTIVIDAD = 'actividad', 'Actividad'
        DECISION = 'decision', 'Decisión'
        CAMBIO = 'cambio', 'Cambio'
        OBSERVACION = 'observacion', 'Observación'

    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name='bitacoras',
        verbose_name='Proyecto'
    )
    tipo = models.CharField(
        max_length=20, choices=TipoChoices.choices, verbose_name='Tipo')
    titulo = models.CharField(max_length=300, verbose_name='Título')
    descripcion = models.TextField(verbose_name='Descripción')
    fecha = models.DateField(verbose_name='Fecha')
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='entradas_bitacora',
        verbose_name='Autor'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Bitácora'
        verbose_name_plural = 'Bitácoras'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.titulo} - {self.fecha}"


class Actividad(models.Model):
    """Acción o tarea ejecutada en el marco de un proyecto o plan de acción."""

    class EstadoChoices(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        EN_PROGRESO = 'en_progreso', 'En Progreso'
        COMPLETADA = 'completada', 'Completada'
        CANCELADA = 'cancelada', 'Cancelada'
        ATRASADA = 'atrasada', 'Atrasada'

    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name='actividades',
        verbose_name='Proyecto'
    )
    titulo = models.CharField(max_length=300, verbose_name='Título')
    descripcion = models.TextField(verbose_name='Descripción')
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='actividades_asignadas',
        verbose_name='Responsable'
    )
    fecha_inicio = models.DateField(verbose_name='Fecha de inicio')
    fecha_fin = models.DateField(verbose_name='Fecha de fin')
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.PENDIENTE,
        verbose_name='Estado'
    )
    porcentaje_avance = models.PositiveIntegerField(
        default=0, verbose_name='Porcentaje de avance')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Actividad'
        verbose_name_plural = 'Actividades'
        ordering = ['fecha_inicio']

    def __str__(self):
        return self.titulo


class Evidencia(models.Model):
    """Archivo que soporta la realización de una actividad o avance."""

    class TipoChoices(models.TextChoices):
        DOCUMENTO = 'documento', 'Documento'
        ACTA = 'acta', 'Acta'
        FOTOGRAFIA = 'fotografia', 'Fotografía'
        VIDEO = 'video', 'Video'
        OTRO = 'otro', 'Otro'

    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name='evidencias',
        verbose_name='Actividad'
    )
    tipo = models.CharField(
        max_length=20, choices=TipoChoices.choices, verbose_name='Tipo')
    titulo = models.CharField(max_length=300, verbose_name='Título')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    archivo = models.FileField(
        upload_to='evidencias/%Y/%m/', verbose_name='Archivo')
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='evidencias_subidas',
        verbose_name='Subido por'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Evidencia'
        verbose_name_plural = 'Evidencias'
        ordering = ['-created_at']

    def __str__(self):
        return self.titulo


class Alerta(models.Model):
    """Notificación automática generada por retraso o incumplimiento."""

    class TipoChoices(models.TextChoices):
        RETRASO_ACTIVIDAD = 'retraso_actividad', 'Retraso en Actividad'
        RETRASO_HITO = 'retraso_hito', 'Retraso en Hito'
        INCUMPLIMIENTO = 'incumplimiento', 'Incumplimiento'
        VENCIMIENTO = 'vencimiento', 'Próximo a Vencer'

    class PrioridadChoices(models.TextChoices):
        BAJA = 'baja', 'Baja'
        MEDIA = 'media', 'Media'
        ALTA = 'alta', 'Alta'
        CRITICA = 'critica', 'Crítica'

    tipo = models.CharField(
        max_length=30, choices=TipoChoices.choices, verbose_name='Tipo')
    prioridad = models.CharField(
        max_length=10,
        choices=PrioridadChoices.choices,
        default=PrioridadChoices.MEDIA,
        verbose_name='Prioridad'
    )
    titulo = models.CharField(max_length=300, verbose_name='Título')
    mensaje = models.TextField(verbose_name='Mensaje')
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alertas',
        verbose_name='Proyecto'
    )
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alertas',
        verbose_name='Actividad'
    )
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='alertas_recibidas',
        verbose_name='Destinatario'
    )
    leida = models.BooleanField(default=False, verbose_name='Leída')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_prioridad_display()}] {self.titulo}"


# ============================================================
# COMPETENCIAS INVESTIGATIVAS
# ============================================================

class CompetenciaInvestigativa(models.Model):
    """Habilidad medible del estudiante en investigación."""

    class NivelChoices(models.TextChoices):
        BASICO = 'basico', 'Básico'
        INTERMEDIO = 'intermedio', 'Intermedio'
        AVANZADO = 'avanzado', 'Avanzado'

    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    descripcion = models.TextField(verbose_name='Descripción')
    nivel = models.CharField(
        max_length=20, choices=NivelChoices.choices, verbose_name='Nivel')
    indicadores = models.TextField(verbose_name='Indicadores de logro')
    semillero = models.ForeignKey(
        Semillero,
        on_delete=models.CASCADE,
        related_name='competencias',
        verbose_name='Semillero'
    )
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Competencia Investigativa'
        verbose_name_plural = 'Competencias Investigativas'
        ordering = ['nombre', 'nivel']

    def __str__(self):
        return f"{self.nombre} - {self.get_nivel_display()}"


class Rubrica(models.Model):
    """Criterio de evaluación asociado a una competencia."""

    competencia = models.ForeignKey(
        CompetenciaInvestigativa,
        on_delete=models.CASCADE,
        related_name='rubricas',
        verbose_name='Competencia'
    )
    criterio = models.CharField(max_length=300, verbose_name='Criterio')
    descripcion_basico = models.TextField(
        verbose_name='Descripción nivel básico')
    descripcion_intermedio = models.TextField(
        verbose_name='Descripción nivel intermedio')
    descripcion_avanzado = models.TextField(
        verbose_name='Descripción nivel avanzado')
    peso = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.0, verbose_name='Peso')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Rúbrica'
        verbose_name_plural = 'Rúbricas'
        ordering = ['competencia', 'criterio']

    def __str__(self):
        return f"{self.criterio} ({self.competencia.nombre})"


class Evaluacion(models.Model):
    """Registro de auto/heteroevaluación de competencias por niveles."""

    class TipoChoices(models.TextChoices):
        AUTOEVALUACION = 'autoevaluacion', 'Autoevaluación'
        HETEROEVALUACION = 'heteroevaluacion', 'Heteroevaluación'

    class NivelAlcanzadoChoices(models.TextChoices):
        BASICO = 'basico', 'Básico'
        INTERMEDIO = 'intermedio', 'Intermedio'
        AVANZADO = 'avanzado', 'Avanzado'

    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='evaluaciones_recibidas',
        verbose_name='Estudiante evaluado'
    )
    evaluador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='evaluaciones_realizadas',
        verbose_name='Evaluador'
    )
    competencia = models.ForeignKey(
        CompetenciaInvestigativa,
        on_delete=models.CASCADE,
        related_name='evaluaciones',
        verbose_name='Competencia'
    )
    tipo = models.CharField(
        max_length=20, choices=TipoChoices.choices, verbose_name='Tipo')
    nivel_alcanzado = models.CharField(
        max_length=20,
        choices=NivelAlcanzadoChoices.choices,
        verbose_name='Nivel alcanzado'
    )
    puntaje = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Puntaje')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    semestre = models.CharField(max_length=10, verbose_name='Semestre')
    fecha = models.DateField(auto_now_add=True, verbose_name='Fecha')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Evaluación'
        verbose_name_plural = 'Evaluaciones'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.estudiante} - {self.competencia} ({self.get_tipo_display()})"


class PerfilInvestigativo(models.Model):
    """Historial longitudinal del estudiante con competencias alcanzadas."""

    estudiante = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_investigativo',
        verbose_name='Estudiante'
    )
    resumen = models.TextField(blank=True, verbose_name='Resumen')
    fortalezas = models.TextField(
        blank=True, verbose_name='Fortalezas identificadas')
    areas_mejora = models.TextField(blank=True, verbose_name='Áreas de mejora')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil Investigativo'
        verbose_name_plural = 'Perfiles Investigativos'

    def __str__(self):
        return f"Perfil de {self.estudiante}"


# ============================================================
# PRODUCCIÓN ACADÉMICA
# ============================================================

class ProduccionAcademica(models.Model):
    """Resultado tangible de la actividad investigativa."""

    class TipoChoices(models.TextChoices):
        ARTICULO = 'articulo', 'Artículo'
        PONENCIA = 'ponencia', 'Ponencia'
        POSTER = 'poster', 'Póster'
        CAPITULO_LIBRO = 'capitulo_libro', 'Capítulo de Libro'
        SOFTWARE = 'software', 'Software'
        PROTOTIPO = 'prototipo', 'Prototipo'
        TRABAJO_GRADO = 'trabajo_grado', 'Trabajo de Grado'
        OTRO = 'otro', 'Otro'

    class EstadoChoices(models.TextChoices):
        EN_ELABORACION = 'en_elaboracion', 'En Elaboración'
        ENVIADO = 'enviado', 'Enviado'
        EN_REVISION = 'en_revision', 'En Revisión'
        ACEPTADO = 'aceptado', 'Aceptado'
        PUBLICADO = 'publicado', 'Publicado'
        RECHAZADO = 'rechazado', 'Rechazado'

    titulo = models.CharField(max_length=500, verbose_name='Título')
    tipo = models.CharField(
        max_length=20, choices=TipoChoices.choices, verbose_name='Tipo')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='producciones',
        verbose_name='Proyecto'
    )
    semillero = models.ForeignKey(
        Semillero,
        on_delete=models.CASCADE,
        related_name='producciones',
        verbose_name='Semillero'
    )
    linea_investigacion = models.ForeignKey(
        LineaInvestigacion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='producciones',
        verbose_name='Línea de investigación'
    )
    autores = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='producciones_academicas',
        verbose_name='Autores'
    )
    doi = models.CharField(max_length=100, blank=True, verbose_name='DOI')
    url_repositorio = models.URLField(
        blank=True, verbose_name='URL del repositorio')
    revista_evento = models.CharField(
        max_length=300, blank=True, verbose_name='Revista / Evento')
    fecha_publicacion = models.DateField(
        null=True, blank=True, verbose_name='Fecha de publicación')
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.EN_ELABORACION,
        verbose_name='Estado'
    )
    archivo = models.FileField(
        upload_to='produccion/%Y/%m/', blank=True, null=True, verbose_name='Archivo')
    certificado = models.FileField(
        upload_to='produccion/certificados/%Y/', blank=True, null=True, verbose_name='Certificado')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Producción Académica'
        verbose_name_plural = 'Producciones Académicas'
        ordering = ['-fecha_publicacion']

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.titulo}"


class ParticipacionEvento(models.Model):
    """Registro de participación en eventos académicos."""

    class TipoParticipacionChoices(models.TextChoices):
        PONENTE = 'ponente', 'Ponente'
        ASISTENTE = 'asistente', 'Asistente'
        ORGANIZADOR = 'organizador', 'Organizador'
        POSTER = 'poster', 'Presentación de Póster'

    produccion = models.ForeignKey(
        ProduccionAcademica,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='participaciones',
        verbose_name='Producción asociada'
    )
    evento = models.CharField(max_length=300, verbose_name='Nombre del evento')
    lugar = models.CharField(max_length=200, blank=True, verbose_name='Lugar')
    fecha_inicio = models.DateField(verbose_name='Fecha de inicio')
    fecha_fin = models.DateField(
        null=True, blank=True, verbose_name='Fecha de fin')
    tipo_participacion = models.CharField(
        max_length=20,
        choices=TipoParticipacionChoices.choices,
        verbose_name='Tipo de participación'
    )
    participante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='participaciones_eventos',
        verbose_name='Participante'
    )
    certificado = models.FileField(
        upload_to='eventos/certificados/%Y/', blank=True, null=True, verbose_name='Certificado')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Participación en Evento'
        verbose_name_plural = 'Participaciones en Eventos'
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"{self.participante} - {self.evento}"


# ============================================================
# CONVOCATORIAS
# ============================================================

class Convocatoria(models.Model):
    """Evento o llamado interno/externo con postulación y seguimiento."""

    class TipoChoices(models.TextChoices):
        INTERNA = 'interna', 'Interna'
        EXTERNA = 'externa', 'Externa'

    class EstadoChoices(models.TextChoices):
        ABIERTA = 'abierta', 'Abierta'
        CERRADA = 'cerrada', 'Cerrada'
        EN_EVALUACION = 'en_evaluacion', 'En Evaluación'
        FINALIZADA = 'finalizada', 'Finalizada'

    titulo = models.CharField(max_length=300, verbose_name='Título')
    descripcion = models.TextField(verbose_name='Descripción')
    tipo = models.CharField(
        max_length=20, choices=TipoChoices.choices, verbose_name='Tipo')
    entidad = models.CharField(
        max_length=200, blank=True, verbose_name='Entidad convocante')
    fecha_apertura = models.DateField(verbose_name='Fecha de apertura')
    fecha_cierre = models.DateField(verbose_name='Fecha de cierre')
    requisitos = models.TextField(blank=True, verbose_name='Requisitos')
    presupuesto = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True, verbose_name='Presupuesto'
    )
    url = models.URLField(blank=True, verbose_name='URL de la convocatoria')
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.ABIERTA,
        verbose_name='Estado'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Convocatoria'
        verbose_name_plural = 'Convocatorias'
        ordering = ['-fecha_apertura']

    def __str__(self):
        return self.titulo


class Postulacion(models.Model):
    """Postulación de un semillero a una convocatoria."""

    class EstadoChoices(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        ACEPTADA = 'aceptada', 'Aceptada'
        RECHAZADA = 'rechazada', 'Rechazada'
        EN_EVALUACION = 'en_evaluacion', 'En Evaluación'

    convocatoria = models.ForeignKey(
        Convocatoria,
        on_delete=models.CASCADE,
        related_name='postulaciones',
        verbose_name='Convocatoria'
    )
    semillero = models.ForeignKey(
        Semillero,
        on_delete=models.CASCADE,
        related_name='postulaciones',
        verbose_name='Semillero'
    )
    estudiantes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='postulaciones',
        verbose_name='Estudiantes postulados'
    )
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='postulaciones',
        verbose_name='Proyecto asociado'
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.PENDIENTE,
        verbose_name='Estado'
    )
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    resultado = models.TextField(blank=True, verbose_name='Resultado')
    fecha_postulacion = models.DateField(
        auto_now_add=True, verbose_name='Fecha de postulación')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Postulación'
        verbose_name_plural = 'Postulaciones'
        ordering = ['-fecha_postulacion']

    def __str__(self):
        return f"{self.semillero} → {self.convocatoria}"


# ============================================================
# INDICADORES E INFORMES
# ============================================================

class Indicador(models.Model):
    """Métrica o KPI para medir desempeño del semillero."""

    class CategoriaChoices(models.TextChoices):
        CULMINACION = 'culminacion', 'Tasa de Culminación'
        PARTICIPACION = 'participacion', 'Participación por Cohorte'
        PERMANENCIA = 'permanencia', 'Permanencia'
        CUMPLIMIENTO = 'cumplimiento', 'Cumplimiento del Plan'
        PRODUCCION = 'produccion', 'Producción Académica'
        COMPETENCIAS = 'competencias', 'Desarrollo de Competencias'

    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    descripcion = models.TextField(verbose_name='Descripción')
    categoria = models.CharField(
        max_length=20, choices=CategoriaChoices.choices, verbose_name='Categoría')
    formula = models.TextField(blank=True, verbose_name='Fórmula de cálculo')
    meta = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Meta')
    unidad_medida = models.CharField(
        max_length=50, blank=True, verbose_name='Unidad de medida')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Indicador'
        verbose_name_plural = 'Indicadores'
        ordering = ['categoria', 'nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_categoria_display()})"


class MedicionIndicador(models.Model):
    """Registro de medición de un indicador por semillero y período."""

    indicador = models.ForeignKey(
        Indicador,
        on_delete=models.CASCADE,
        related_name='mediciones',
        verbose_name='Indicador'
    )
    semillero = models.ForeignKey(
        Semillero,
        on_delete=models.CASCADE,
        related_name='mediciones_indicadores',
        verbose_name='Semillero'
    )
    semestre = models.CharField(max_length=10, verbose_name='Semestre')
    valor = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor medido')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mediciones_registradas',
        verbose_name='Registrado por'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Medición de Indicador'
        verbose_name_plural = 'Mediciones de Indicadores'
        unique_together = ['indicador', 'semillero', 'semestre']
        ordering = ['-semestre']

    def __str__(self):
        return f"{self.indicador.nombre} - {self.semillero} ({self.semestre}): {self.valor}"


class Informe(models.Model):
    """Documento generado que consolida actividades, proyectos y resultados."""

    class TipoChoices(models.TextChoices):
        SEMESTRAL = 'semestral', 'Semestral'
        ANUAL = 'anual', 'Anual'
        ESPECIAL = 'especial', 'Especial'

    class EstadoChoices(models.TextChoices):
        BORRADOR = 'borrador', 'Borrador'
        GENERADO = 'generado', 'Generado'
        REVISADO = 'revisado', 'Revisado'
        APROBADO = 'aprobado', 'Aprobado'

    semillero = models.ForeignKey(
        Semillero,
        on_delete=models.CASCADE,
        related_name='informes',
        verbose_name='Semillero'
    )
    titulo = models.CharField(max_length=300, verbose_name='Título')
    tipo = models.CharField(
        max_length=20, choices=TipoChoices.choices, verbose_name='Tipo')
    semestre = models.CharField(
        max_length=10, verbose_name='Semestre / Período')
    contenido = models.TextField(blank=True, verbose_name='Contenido')
    archivo = models.FileField(
        upload_to='informes/%Y/%m/', blank=True, null=True, verbose_name='Archivo')
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.BORRADOR,
        verbose_name='Estado'
    )
    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='informes_generados',
        verbose_name='Generado por'
    )
    fecha_generacion = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de generación')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Informe'
        verbose_name_plural = 'Informes'
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f"{self.titulo} - {self.semillero} ({self.semestre})"
