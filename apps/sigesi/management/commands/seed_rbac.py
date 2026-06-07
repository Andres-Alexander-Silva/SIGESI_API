"""Siembra y reconcilia los Menús, Opciones y Permisos RBAC de las rutas del frontend.

La barra lateral del cliente React y el gating de botones por acción se
construyen *a partir de los datos* de las tablas RBAC (``Menu → Opcion →
Permiso``), que el frontend consulta por rol activo vía
``GET /api/v1/config/users/mis-permisos/``. Si una ruta del frontend no tiene su
fila ``Opcion``, esa ruta nunca aparece en el menú y todos sus ``can(url, accion)``
devuelven ``false``.

``MENUS`` y ``OPCIONES`` declaran el conjunto **completo** (los 9 menús y las 28
opciones de todas las rutas, incluidas las 6 + 8 que sembró la migración
``0003_data_menus_opciones_permisos``): el comando crea lo que falte y actualiza
los valores de lo existente que difiera. ``PERMISOS`` cubre las opciones nuevas
(los permisos de las 8 opciones originales los gobierna la migración 0003).

Decisiones de diseño:
- ``Opcion.url`` = la ruta real del frontend (para que la navegación del sidebar
  funcione). Tres páginas consultan ``can()`` con una cadena distinta a su ruta
  (``/produccion``, ``/evaluaciones-proyecto``, ``/cronograma``); esa
  inconsistencia es del frontend y no se acomoda aquí.
- Los flags CRUD por rol se infieren de las clases ``*RolePermission`` en
  ``apps/sigesi/decorators/permissions.py`` (ver comentarios por opción).

Es idempotente y reconciliador: las filas se ubican por su clave natural (Menu
por ``nombre``, Opcion por ``url``, Permiso por ``(opcion, rol)``); si faltan se
crean y, si existen pero con valores distintos a los declarados, se actualizan
solo los campos que cambiaron (icono del menú; menú/nombre de la opción; flags
``puede_*`` del permiso). El ``estado`` de la opción no se toca (es un
interruptor administrable). Volver a ejecutarlo no crea duplicados.

Uso:
    python manage.py seed_rbac            # crea lo que falte y reconcilia diferencias
    python manage.py seed_rbac --dry-run  # muestra los cambios y revierte
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.sigesi.models import Menu, Opcion, Permiso


# ── Menús ─────────────────────────────────────────────────────────────────────
# (nombre, icono). Conjunto COMPLETO de menús (los sembrados por la migración 0003
# + los nuevos): el comando crea los que falten y reconcilia el icono de los que
# existan. Los íconos deben ser únicos (constraint del modelo) y resolver en
# SIGESI_CLIENT/src/utils/iconMap.tsx (se quita el prefijo "fa-" y separadores).
MENUS = [
    ('Dashboard',                'fa-gauge'),
    ('Semilleros',               'fa-flask'),
    ('Grupos de Investigación',  'fa-users'),
    ('Proyectos',                'fa-tasks'),
    ('Planeación',               'fa-bullseye'),
    ('Competencias',             'psychology'),
    ('Convocatorias',            'fa-bullhorn'),
    ('Reportes',                 'fa-chart-bar'),
    ('Configuración',            'fa-gear'),
]

# ── Opciones ──────────────────────────────────────────────────────────────────
# (menu_nombre, nombre_opcion, url). Conjunto COMPLETO de opciones (las sembradas
# por la migración 0003 + las nuevas): el comando crea las que falten y reconcilia
# menú/nombre de las que existan (sin tocar `estado`). El menú se busca por nombre
# y debe estar declarado en MENUS.
OPCIONES = [
    # Dashboard
    ('Dashboard',                'Dashboard',                   '/dashboard'),

    # Semilleros
    ('Semilleros',               'Semilleros',                  '/semilleros'),
    ('Semilleros',               'Líneas de Investigación',     '/lineas_investigacion'),
    ('Semilleros',               'Inscripción',                 '/inscripcion'),
    ('Semilleros',               'Gestionar Miembros',          '/gestionar_miembros'),

    # Grupos de Investigación
    ('Grupos de Investigación',  'Grupos',                      '/grupos'),
    ('Grupos de Investigación',  'Programas Académicos',        '/programas_academicos'),

    # Proyectos
    ('Proyectos',                'Proyectos',                   '/proyectos'),
    ('Proyectos',                'Actividades',                 '/actividades'),
    ('Proyectos',                'Avances',                     '/avances'),
    ('Proyectos',                'Cronograma de Proyecto',      '/cronograma_proyecto'),
    ('Proyectos',                'Evaluaciones de Proyecto',    '/evaluaciones_proyecto'),
    ('Proyectos',                'Producción Académica',        '/produccion_academica'),

    # Planeación
    ('Planeación',               'Plan Estratégico',            '/plan_estrategico'),
    ('Planeación',               'Plan de Acción',              '/plan_accion'),
    ('Planeación',               'Cronograma',                  '/cronograma'),

    # Competencias
    ('Competencias',             'Competencias Investigativas', '/competencias_investigativas'),
    ('Competencias',             'Evaluaciones Investigativas', '/evaluaciones_investigativas'),
    ('Competencias',             'Estadísticas de Competencias', '/competencias_estadisticas'),
    ('Competencias',             'Perfil Investigativo',        '/perfil_investigativo'),

    # Convocatorias (flujo de eventos: Evento → Convocatoria → Postulación → Participación)
    ('Convocatorias',            'Eventos',                     '/eventos'),
    ('Convocatorias',            'Convocatorias',               '/convocatorias'),
    ('Convocatorias',            'Postulaciones',               '/postulaciones'),
    ('Convocatorias',            'Participaciones en Eventos',  '/participaciones_evento'),

    # Reportes
    ('Reportes',                 'Reportes',                    '/reportes'),
    ('Reportes',                 'Analítica',                   '/analitica'),

    # Configuración
    ('Configuración',            'Usuarios',                    '/configuracion/usuarios'),
    ('Configuración',            'Menús',                       '/configuracion/menus'),
    ('Configuración',            'Opciones',                    '/configuracion/opciones'),
    ('Configuración',            'Permisos',                    '/configuracion/permisos'),
    ('Configuración',            'Auditoría',                   '/auditoria'),
]

# ── Permisos ──────────────────────────────────────────────────────────────────
# (url, rol, puede_consultar, puede_crear, puede_actualizar, puede_eliminar).
# Inferidos de las clases *RolePermission (apps/sigesi/decorators/permissions.py).
# Un rol sin fila para una opción simplemente no la verá.
#
# Notas:
# - lider_estudiantil es solo-lectura en /evaluaciones_proyecto:
#   EvaluacionProyectoPermission bloquea escritura a quien tenga rol 'estudiante'
#   sin rol de director, y User.save() fuerza a 'lider_estudiantil' a llevar
#   también 'estudiante'.
# - /lineas_investigacion y /grupos solo usan IsAuthenticated en el backend (sin
#   gate por rol): la matriz de abajo es un ENDURECIMIENTO razonable, no un
#   espejo. La API hoy deja escribir a cualquier autenticado (gap a corregir
#   aparte).
PERMISOS = [
    # url, rol, C, Cr, A, E
    # ── /proyectos — ProyectoRolePermission ──────────────────────────────────
    ('/proyectos',                  'administrador',      True,  True,  True,  True),
    ('/proyectos',                  'director_grupo',     True,  True,  True,  True),
    ('/proyectos',                  'director_semillero', True,  True,  True,  True),
    ('/proyectos',                  'lider_estudiantil',  True,  True,  True,  False),
    ('/proyectos',                  'estudiante',         True,  True,  True,  False),

    # ── /lineas_investigacion — IsAuthenticated (endurecido) ─────────────────
    ('/lineas_investigacion',       'administrador',      True,  True,  True,  True),
    ('/lineas_investigacion',       'director_grupo',     True,  True,  True,  True),
    ('/lineas_investigacion',       'director_semillero', True,  False, False, False),
    ('/lineas_investigacion',       'lider_estudiantil',  True,  False, False, False),
    ('/lineas_investigacion',       'estudiante',         True,  False, False, False),

    # ── /inscripcion — InscripcionRolePermission ─────────────────────────────
    ('/inscripcion',                'administrador',      True,  True,  True,  True),
    ('/inscripcion',                'director_grupo',     True,  False, False, False),
    ('/inscripcion',                'director_semillero', True,  True,  False, False),
    ('/inscripcion',                'lider_estudiantil',  True,  False, False, False),
    ('/inscripcion',                'estudiante',         True,  True,  False, True),

    # ── /gestionar_miembros — InscripcionRolePermission (herramienta director) ─
    ('/gestionar_miembros',         'administrador',      True,  True,  True,  True),
    ('/gestionar_miembros',         'director_grupo',     True,  False, False, False),
    ('/gestionar_miembros',         'director_semillero', True,  True,  True,  False),

    # ── /actividades — ActividadRolePermission ───────────────────────────────
    ('/actividades',                'administrador',      True,  True,  True,  True),
    ('/actividades',                'director_grupo',     True,  True,  True,  True),
    ('/actividades',                'director_semillero', True,  True,  True,  True),
    ('/actividades',                'lider_estudiantil',  True,  True,  True,  True),
    ('/actividades',                'estudiante',         True,  False, False, False),

    # ── /avances — EvidenciaRolePermission ───────────────────────────────────
    ('/avances',                    'administrador',      True,  True,  True,  True),
    ('/avances',                    'director_grupo',     True,  True,  True,  True),
    ('/avances',                    'director_semillero', True,  True,  True,  True),
    ('/avances',                    'lider_estudiantil',  True,  True,  True,  True),
    ('/avances',                    'estudiante',         True,  True,  True,  False),

    # ── /produccion_academica — ProduccionAcademicaRolePermission ────────────
    ('/produccion_academica',       'administrador',      True,  True,  True,  True),
    ('/produccion_academica',       'director_grupo',     True,  True,  True,  True),
    ('/produccion_academica',       'director_semillero', True,  True,  True,  True),
    ('/produccion_academica',       'lider_estudiantil',  True,  True,  True,  True),
    ('/produccion_academica',       'estudiante',         True,  False, False, False),

    # ── /programas_academicos — AdminOrReadOnlyPermission ────────────────────
    ('/programas_academicos',       'administrador',      True,  True,  True,  True),
    ('/programas_academicos',       'director_grupo',     True,  False, False, False),
    ('/programas_academicos',       'director_semillero', True,  False, False, False),
    ('/programas_academicos',       'lider_estudiantil',  True,  False, False, False),
    ('/programas_academicos',       'estudiante',         True,  False, False, False),

    # ── /cronograma_proyecto — CronogramaProyectoRolePermission ──────────────
    ('/cronograma_proyecto',        'administrador',      True,  True,  True,  True),
    ('/cronograma_proyecto',        'director_grupo',     True,  True,  True,  True),
    ('/cronograma_proyecto',        'director_semillero', True,  True,  True,  True),
    ('/cronograma_proyecto',        'lider_estudiantil',  True,  True,  True,  True),
    ('/cronograma_proyecto',        'estudiante',         True,  False, False, False),

    # ── /evaluaciones_proyecto — EvaluacionProyectoPermission ────────────────
    ('/evaluaciones_proyecto',      'administrador',      True,  True,  True,  True),
    ('/evaluaciones_proyecto',      'director_grupo',     True,  True,  True,  True),
    ('/evaluaciones_proyecto',      'director_semillero', True,  True,  True,  True),
    ('/evaluaciones_proyecto',      'lider_estudiantil',  True,  False, False, False),
    ('/evaluaciones_proyecto',      'estudiante',         True,  False, False, False),

    # ── /plan_accion — PlanAccionRolePermission ──────────────────────────────
    ('/plan_accion',                'administrador',      True,  True,  True,  True),
    ('/plan_accion',                'director_grupo',     True,  True,  True,  True),
    ('/plan_accion',                'director_semillero', True,  True,  True,  True),
    ('/plan_accion',                'lider_estudiantil',  True,  False, False, False),
    ('/plan_accion',                'estudiante',         True,  False, False, False),

    # ── /plan_estrategico — PlanEstrategicoRolePermission ────────────────────
    # (el cambio de 'estado' lo restringe adicionalmente el serializer)
    ('/plan_estrategico',           'administrador',      True,  True,  True,  True),
    ('/plan_estrategico',           'director_grupo',     True,  True,  True,  True),
    ('/plan_estrategico',           'director_semillero', True,  True,  True,  True),
    ('/plan_estrategico',           'lider_estudiantil',  True,  False, False, False),
    ('/plan_estrategico',           'estudiante',         True,  False, False, False),

    # ── /cronograma — CronogramaRolePermission ───────────────────────────────
    ('/cronograma',                 'administrador',      True,  True,  True,  True),
    ('/cronograma',                 'director_grupo',     True,  True,  True,  True),
    ('/cronograma',                 'director_semillero', True,  True,  True,  True),
    ('/cronograma',                 'lider_estudiantil',  True,  False, False, False),
    ('/cronograma',                 'estudiante',         True,  False, False, False),

    # ── /competencias_investigativas — CompetenciaInvestigativaRolePermission ─
    ('/competencias_investigativas', 'administrador',      True,  True,  True,  True),
    ('/competencias_investigativas', 'director_grupo',     True,  False, False, False),
    ('/competencias_investigativas', 'director_semillero', True,  False, True,  False),
    ('/competencias_investigativas', 'lider_estudiantil',  True,  False, False, False),
    ('/competencias_investigativas', 'estudiante',         True,  False, False, False),

    # ── /evaluaciones_investigativas — EvaluacionRolePermission ──────────────
    ('/evaluaciones_investigativas', 'administrador',      True,  True,  True,  True),
    ('/evaluaciones_investigativas', 'director_grupo',     True,  False, False, False),
    ('/evaluaciones_investigativas', 'director_semillero', True,  True,  True,  True),
    ('/evaluaciones_investigativas', 'lider_estudiantil',  True,  False, False, False),
    ('/evaluaciones_investigativas', 'estudiante',         True,  False, False, False),

    # ── /competencias_estadisticas — dashboard de competencias (lectura) ─────
    ('/competencias_estadisticas',  'administrador',      True,  False, False, False),
    ('/competencias_estadisticas',  'director_grupo',     True,  False, False, False),
    ('/competencias_estadisticas',  'director_semillero', True,  False, False, False),
    ('/competencias_estadisticas',  'lider_estudiantil',  True,  False, False, False),
    ('/competencias_estadisticas',  'estudiante',         True,  False, False, False),

    # ── /perfil_investigativo — PerfilInvestigativoRolePermission ────────────
    ('/perfil_investigativo',       'administrador',      True,  True,  True,  True),
    ('/perfil_investigativo',       'director_grupo',     True,  False, False, False),
    ('/perfil_investigativo',       'director_semillero', True,  False, False, False),
    ('/perfil_investigativo',       'lider_estudiantil',  True,  False, False, False),
    ('/perfil_investigativo',       'estudiante',         True,  False, False, False),

    # ── /analitica — dashboard analítico (lectura: admin + directores) ───────
    ('/analitica',                  'administrador',      True,  False, False, False),
    ('/analitica',                  'director_grupo',     True,  False, False, False),
    ('/analitica',                  'director_semillero', True,  False, False, False),

    # ── /configuracion/opciones — config admin ───────────────────────────────
    ('/configuracion/opciones',     'administrador',      True,  True,  True,  True),

    # ── /auditoria — AuditoriaPermission (solo admin, lectura) ───────────────
    ('/auditoria',                  'administrador',      True,  False, False, False),

    # ── /eventos — AdminOrReadOnlyPermission (admin escribe, todos leen) ──────
    ('/eventos',                    'administrador',      True,  True,  True,  True),
    ('/eventos',                    'director_grupo',     True,  False, False, False),
    ('/eventos',                    'director_semillero', True,  False, False, False),
    ('/eventos',                    'lider_estudiantil',  True,  False, False, False),
    ('/eventos',                    'estudiante',         True,  False, False, False),

    # ── /postulaciones — PostulacionRolePermission ───────────────────────────
    # director_grupo no crea/edita por CRUD, pero resuelve (aprobar/rechazar);
    # 'aprobar' en el frontend se deriva de puede_actualizar.
    ('/postulaciones',              'administrador',      True,  True,  True,  True),
    ('/postulaciones',              'director_grupo',     True,  False, True,  False),
    ('/postulaciones',              'director_semillero', True,  True,  True,  True),
    ('/postulaciones',              'lider_estudiantil',  True,  False, False, False),
    ('/postulaciones',              'estudiante',         True,  False, False, False),

    # ── /participaciones_evento — ParticipacionEventoRolePermission ──────────
    ('/participaciones_evento',     'administrador',      True,  True,  True,  True),
    ('/participaciones_evento',     'director_grupo',     True,  True,  True,  True),
    ('/participaciones_evento',     'director_semillero', True,  True,  True,  True),
    ('/participaciones_evento',     'lider_estudiantil',  True,  True,  True,  True),
    ('/participaciones_evento',     'estudiante',         True,  False, False, False),
]


class Command(BaseCommand):
    """Inyecta y reconcilia los Menús/Opciones/Permisos RBAC de las rutas del frontend."""

    help = (
        'Crea los Menús, Opciones y Permisos RBAC que faltan para cubrir las '
        'rutas del frontend y actualiza los existentes cuyos valores difieran '
        'de los declarados. Idempotente.'
    )

    def add_arguments(self, parser):
        """Registra el flag ``--dry-run`` para previsualizar sin persistir."""
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se crearía y revierte la transacción sin guardar.',
        )

    def handle(self, *args, **options):
        """Crea y reconcilia menús, opciones y permisos dentro de una transacción.

        Si una fila ya existe (Menu por ``nombre``, Opcion por ``url``, Permiso
        por ``(opcion, rol)``) pero alguno de sus valores declarados difiere, se
        actualiza solo el/los campo(s) que cambiaron. Con ``--dry-run`` ejecuta
        todo y revierte, dejando la base de datos intacta. Imprime un resumen de
        creados / actualizados / sin cambios por tabla.
        """
        dry_run = options['dry_run']
        stats = {
            'menus':    {'creados': 0, 'actualizados': 0, 'sin_cambios': 0},
            'opciones': {'creados': 0, 'actualizados': 0, 'sin_cambios': 0},
            'permisos': {'creados': 0, 'actualizados': 0, 'sin_cambios': 0},
        }

        def _reconciliar(obj, valores, tabla):
            """Aplica los `valores` que difieran en `obj` y contabiliza el resultado."""
            cambios = [k for k, v in valores.items() if getattr(obj, k) != v]
            if cambios:
                for k in cambios:
                    setattr(obj, k, valores[k])
                obj.save(update_fields=cambios)
                stats[tabla]['actualizados'] += 1
            else:
                stats[tabla]['sin_cambios'] += 1

        class _Rollback(Exception):
            """Señal interna para revertir en modo --dry-run."""

        try:
            with transaction.atomic():
                # 1) Menús: crear los que falten; reconciliar el icono si difiere.
                menus = {m.nombre: m for m in Menu.objects.all()}
                for nombre, icono in MENUS:
                    obj, creado = Menu.objects.get_or_create(
                        nombre=nombre, defaults={'icono': icono, 'estado': True}
                    )
                    menus[nombre] = obj
                    if creado:
                        stats['menus']['creados'] += 1
                    else:
                        _reconciliar(obj, {'icono': icono}, 'menus')

                # 2) Opciones: crear las que falten; reconciliar menú y nombre si
                #    difieren (no se toca `estado`, que es un interruptor administrable).
                opciones = {}
                for menu_nombre, nombre, url in OPCIONES:
                    menu = menus.get(menu_nombre)
                    if menu is None:
                        raise ValueError(
                            f"El menú '{menu_nombre}' no está declarado en MENUS."
                        )
                    obj, creado = Opcion.objects.get_or_create(
                        url=url,
                        defaults={'menu': menu, 'nombre': nombre, 'estado': True},
                    )
                    opciones[url] = obj
                    if creado:
                        stats['opciones']['creados'] += 1
                    else:
                        _reconciliar(obj, {'menu': menu, 'nombre': nombre}, 'opciones')

                # 3) Permisos: crear los nuevos; reconciliar los flags puede_* si difieren.
                for url, rol, c, cr, a, e in PERMISOS:
                    opcion = opciones.get(url)
                    if opcion is None:
                        # La opción podría existir de una corrida previa; resuélvela.
                        opcion = Opcion.objects.get(url=url)
                    flags = {
                        'puede_consultar':  c,
                        'puede_crear':      cr,
                        'puede_actualizar': a,
                        'puede_eliminar':   e,
                    }
                    obj, creado = Permiso.objects.get_or_create(
                        opcion=opcion, rol=rol, defaults=flags,
                    )
                    if creado:
                        stats['permisos']['creados'] += 1
                    else:
                        _reconciliar(obj, flags, 'permisos')

                if dry_run:
                    raise _Rollback()
        except _Rollback:
            self.stdout.write(self.style.WARNING('--dry-run: cambios revertidos.'))

        self.stdout.write(self.style.SUCCESS('Resumen RBAC:'))
        for tabla, s in stats.items():
            self.stdout.write(
                f"  {tabla:9}  creados: {s['creados']:3}   "
                f"actualizados: {s['actualizados']:3}   "
                f"sin cambios: {s['sin_cambios']:3}"
            )
        if not dry_run:
            self.stdout.write(self.style.SUCCESS('Listo.'))
