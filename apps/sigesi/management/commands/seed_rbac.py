"""Comando idempotente para sembrar el RBAC del módulo documental (HU-021).

Antes de este comando, `Menu`/`Opcion`/`Permiso` solo se cargaban desde la
migración de datos `0003_data_menus_opciones_permisos.py` (Dashboard,
Semilleros, Grupos, Convocatorias, Reportes, Configuración). Ese archivo no
se toca aquí: sigue siendo la fuente de verdad de esos seis menús base.

Este comando cubre las rutas del módulo de Gestión de Evidencias y
Repositorio Académico (HU-021) que el cliente ya invoca vía `can(url, accion)`
pero para las que nunca existió una fila `Opcion`: /avances, /produccion,
/participaciones_evento, /eventos, /proyectos y /actividades. Sin esas filas,
`can()` falla en cerrado (ver `PermissionsContext.tsx` en SIGESI_CLIENT) y
ningún rol —ni el administrador— puede escribir en esas páginas.

Los strings de `url` deben coincidir EXACTAMENTE con los que el cliente
invoca. Tres de ellos son deliberadamente distintos del nombre del recurso
en el backend (documentado en el CLAUDE.md de la raíz del monorepo):
`/produccion` (no `/producciones-academicas`), `/evaluaciones-proyecto` y
`/cronograma` para otras páginas no cubiertas aquí.

Uso:
    python manage.py seed_rbac

Es seguro reejecutarlo cuantas veces haga falta (usa ``update_or_create``
sobre nombre/url/rol+opción) — hacedlo después de agregar una nueva ruta
documental al frontend.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.sigesi.models import Menu, Opcion, Permiso, User

R = User.RolChoices

# (nombre, icono) — el icono debe ser único entre todos los Menu existentes
# (Menu.icono tiene unique=True). Los seis menús base usan fa-gauge, fa-flask,
# fa-users, fa-bullhorn, fa-chart-bar y fa-gear.
MENUS = [
    ('Producción y Evidencias', 'fa-folder-open'),
]

# (menu_nombre, nombre_opcion, url)
OPCIONES = [
    ('Producción y Evidencias', 'Avances',                    '/avances'),
    ('Producción y Evidencias', 'Producción Académica',       '/produccion'),
    ('Producción y Evidencias', 'Participaciones en Eventos', '/participaciones_evento'),
    ('Producción y Evidencias', 'Eventos',                    '/eventos'),
    ('Producción y Evidencias', 'Proyectos',                  '/proyectos'),
    ('Producción y Evidencias', 'Actividades',                '/actividades'),
]

# (url_opcion, rol, puede_consultar, puede_crear, puede_actualizar, puede_eliminar)
#
# Fundamentado en las clases de permiso ya existentes en
# apps/sigesi/decorators/permissions.py (no inventado desde cero):
#   - /avances:        EvidenciaPermission — cualquier responsable de la
#     actividad (cualquier rol) puede crear/editar; eliminar reservado a
#     administrador/directores (los roles "estudiante" quedan además
#     bloqueados en el cliente por el flag `isStudent`, independientemente
#     de este valor).
#   - /produccion:     ProduccionAcademicaViewSet._puede_escribir_en_proyecto
#     — solo administrador o el director/líder del proyecto; el cliente ya
#     restringe además con ROLES_ESCRITURA = [administrador, director_grupo,
#     director_semillero].
#   - /participaciones_evento y /eventos: matriz calcada de los fallbacks
#     `activeRole === '...'` que ya traían ParticipacionesEventoPage.tsx y
#     EventosPage.tsx antes de esta fase.
#   - /proyectos:      ProyectoRolePermission — POST/PUT/PATCH abiertos a
#     todo autenticado; DELETE explícitamente denegado a estudiante y
#     líder_estudiantil ("No pueden eliminar").
#   - /actividades:    ActividadRolePermission — estudiante solo lectura;
#     administrador, directores y líder_estudiantil con CRUD completo.
PERMISOS = [
    # ── /avances (Evidencia) ──────────────────────────────────────────────
    ('/avances', R.ADMINISTRADOR,       True, True,  True,  True),
    ('/avances', R.DIRECTOR_GRUPO,      True, True,  True,  True),
    ('/avances', R.DIRECTOR_SEMILLERO,  True, True,  True,  True),
    ('/avances', R.LIDER_ESTUDIANTIL,   True, True,  True,  False),
    ('/avances', R.ESTUDIANTE,          True, True,  True,  False),

    # ── /produccion (Producción Académica) ────────────────────────────────
    ('/produccion', R.ADMINISTRADOR,       True, True,  True,  True),
    ('/produccion', R.DIRECTOR_GRUPO,      True, True,  True,  True),
    ('/produccion', R.DIRECTOR_SEMILLERO,  True, True,  True,  True),
    ('/produccion', R.LIDER_ESTUDIANTIL,   True, False, False, False),
    ('/produccion', R.ESTUDIANTE,          True, False, False, False),

    # ── /participaciones_evento ────────────────────────────────────────────
    ('/participaciones_evento', R.ADMINISTRADOR,       True, True,  True,  True),
    ('/participaciones_evento', R.DIRECTOR_GRUPO,      True, True,  True,  True),
    ('/participaciones_evento', R.DIRECTOR_SEMILLERO,  True, True,  True,  True),
    ('/participaciones_evento', R.LIDER_ESTUDIANTIL,   True, True,  True,  True),
    ('/participaciones_evento', R.ESTUDIANTE,          True, False, False, False),

    # ── /eventos (catálogo administrado) ───────────────────────────────────
    ('/eventos', R.ADMINISTRADOR,       True, True,  True,  True),
    ('/eventos', R.DIRECTOR_GRUPO,      True, True,  True,  True),
    ('/eventos', R.DIRECTOR_SEMILLERO,  True, False, False, False),
    ('/eventos', R.LIDER_ESTUDIANTIL,   True, False, False, False),
    ('/eventos', R.ESTUDIANTE,          True, False, False, False),

    # ── /proyectos ──────────────────────────────────────────────────────────
    ('/proyectos', R.ADMINISTRADOR,       True, True, True, True),
    ('/proyectos', R.DIRECTOR_GRUPO,      True, True, True, True),
    ('/proyectos', R.DIRECTOR_SEMILLERO,  True, True, True, True),
    ('/proyectos', R.LIDER_ESTUDIANTIL,   True, True, True, False),
    ('/proyectos', R.ESTUDIANTE,          True, True, True, False),

    # ── /actividades ────────────────────────────────────────────────────────
    ('/actividades', R.ADMINISTRADOR,       True, True,  True,  True),
    ('/actividades', R.DIRECTOR_GRUPO,      True, True,  True,  True),
    ('/actividades', R.DIRECTOR_SEMILLERO,  True, True,  True,  True),
    ('/actividades', R.LIDER_ESTUDIANTIL,   True, True,  True,  True),
    ('/actividades', R.ESTUDIANTE,          True, False, False, False),
]


class Command(BaseCommand):
    help = (
        'Siembra (o actualiza) el RBAC del modulo documental de HU-021: '
        'Menu/Opcion/Permiso para /avances, /produccion, '
        '/participaciones_evento, /eventos, /proyectos y /actividades.'
    )

    @transaction.atomic
    def handle(self, *args, **options):
        menus = {}
        for nombre, icono in MENUS:
            obj, created = Menu.objects.update_or_create(
                nombre=nombre, defaults={'icono': icono, 'estado': True},
            )
            menus[nombre] = obj
            self._log(created, 'Menu', nombre)

        opciones = {}
        for menu_nombre, nombre, url in OPCIONES:
            obj, created = Opcion.objects.update_or_create(
                url=url,
                defaults={'menu': menus[menu_nombre], 'nombre': nombre, 'estado': True},
            )
            opciones[url] = obj
            self._log(created, 'Opcion', url)

        for url, rol, consultar, crear, actualizar, eliminar in PERMISOS:
            Permiso.objects.update_or_create(
                opcion=opciones[url], rol=rol,
                defaults={
                    'puede_consultar':  consultar,
                    'puede_crear':      crear,
                    'puede_actualizar': actualizar,
                    'puede_eliminar':   eliminar,
                },
            )
            self._log(None, 'Permiso', f'{rol} -> {url}')

        # Limpieza de H1: la migracion 0003 sembro permisos para el rol
        # 'comite', que nunca existio en User.RolChoices ni se puede asignar
        # a ningun usuario (filas huerfanas).
        roles_validos = set(R.values)
        huerfanos, _ = Permiso.objects.exclude(rol__in=roles_validos).delete()
        if huerfanos:
            self.stdout.write(f'  Eliminados {huerfanos} permisos con rol invalido (p. ej. "comite").')

        self.stdout.write(self.style.SUCCESS(
            'RBAC del modulo documental sembrado correctamente '
            f'({len(OPCIONES)} opciones, {len(PERMISOS)} permisos).'
        ))

    def _log(self, created, tipo, etiqueta):
        if created is None:
            self.stdout.write(f'  {tipo}: {etiqueta}')
            return
        accion = 'creado' if created else 'actualizado'
        self.stdout.write(f'  {tipo} {accion}: {etiqueta}')
