"""
Data migration: carga inicial de Menús, Opciones y Permisos por rol.

Estructura:
  Menu        → nombre, icono
  Opcion      → menu, nombre, url
  Permiso     → rol, opcion, puede_consultar, puede_crear,
                puede_actualizar, puede_eliminar
"""

from django.db import migrations


MENUS = [
    # (nombre, icono)
    ('Dashboard',               'fa-gauge'),
    ('Semilleros',              'fa-flask'),
    ('Grupos de Investigación', 'fa-users'),
    ('Convocatorias',           'fa-bullhorn'),
    ('Reportes',                'fa-chart-bar'),
    ('Configuración',           'fa-gear'),
]

# (menu_nombre, nombre_opcion, url)
OPCIONES = [
    ('Dashboard',               'Dashboard',    '/dashboard'),

    ('Semilleros',              'Semilleros',   '/semilleros'),

    ('Grupos de Investigación', 'Grupos',       '/grupos'),

    ('Convocatorias',           'Convocatorias', '/convocatorias'),

    ('Reportes',                'Reportes',     '/reportes'),

    ('Configuración',           'Usuarios',     '/configuracion/usuarios'),
    ('Configuración',           'Menús',        '/configuracion/menus'),
    ('Configuración',           'Permisos',     '/configuracion/permisos'),
]

# (url_opcion, rol, puede_consultar, puede_crear, puede_actualizar, puede_eliminar)
PERMISOS = [
    # ── ADMINISTRADOR: acceso total ──────────────────────────────────────────
    ('/dashboard',                  'administrador', True,  False, False, False),
    ('/semilleros',                 'administrador', True,  True,  True,  True),
    ('/grupos',                     'administrador', True,  True,  True,  True),
    ('/convocatorias',              'administrador', True,  True,  True,  True),
    ('/reportes',                   'administrador', True,  False, False, False),
    ('/configuracion/usuarios',     'administrador', True,  True,  True,  True),
    ('/configuracion/menus',        'administrador', True,  True,  True,  True),
    ('/configuracion/permisos',     'administrador', True,  True,  True,  True),

    # ── COMITÉ DE INVESTIGACIÓN ──────────────────────────────────────────────
    ('/dashboard',                  'comite', True,  False, False, False),
    ('/semilleros',                 'comite', True,  False, False, False),
    ('/grupos',                     'comite', True,  False, False, False),
    ('/convocatorias',              'comite', True,  True,  True,  False),
    ('/reportes',                   'comite', True,  False, False, False),

    # ── DIRECTOR DE GRUPO ────────────────────────────────────────────────────
    ('/dashboard',                  'director_grupo', True,  False, False, False),
    ('/semilleros',                 'director_grupo', True,  True,  True,  False),
    ('/grupos',                     'director_grupo', True,  False, True,  False),
    ('/convocatorias',              'director_grupo', True,  True,  True,  False),
    ('/reportes',                   'director_grupo', True,  False, False, False),

    # ── DIRECTOR DE SEMILLERO ────────────────────────────────────────────────
    ('/dashboard',                  'director_semillero', True,  False, False, False),
    ('/semilleros',                 'director_semillero', True,  False, True,  False),
    ('/grupos',                     'director_semillero', True,  False, False, False),
    ('/convocatorias',              'director_semillero', True,  False, False, False),
    ('/reportes',                   'director_semillero', True,  False, False, False),

    # ── LÍDER ESTUDIANTIL ────────────────────────────────────────────────────
    ('/dashboard',                  'lider_estudiantil', True,  False, False, False),
    ('/semilleros',                 'lider_estudiantil', True,  False, False, False),
    ('/grupos',                     'lider_estudiantil', True,  False, False, False),
    ('/convocatorias',              'lider_estudiantil', True,  False, False, False),

    # ── ESTUDIANTE ───────────────────────────────────────────────────────────
    ('/dashboard',                  'estudiante', True,  False, False, False),
    ('/semilleros',                 'estudiante', True,  False, False, False),
    ('/grupos',                     'estudiante', True,  False, False, False),
    ('/convocatorias',              'estudiante', True,  False, False, False),
]


def cargar_datos(apps, schema_editor):
    Menu    = apps.get_model('sigesi', 'Menu')
    Opcion  = apps.get_model('sigesi', 'Opcion')
    Permiso = apps.get_model('sigesi', 'Permiso')

    menus = {}
    for nombre, icono in MENUS:
        obj, _ = Menu.objects.get_or_create(nombre=nombre, defaults={'icono': icono})
        menus[nombre] = obj

    opciones = {}
    for menu_nombre, nombre, url in OPCIONES:
        obj, _ = Opcion.objects.get_or_create(
            url=url,
            defaults={'menu': menus[menu_nombre], 'nombre': nombre, 'estado': True},
        )
        opciones[url] = obj

    for url, rol, c, cr, a, e in PERMISOS:
        Permiso.objects.get_or_create(
            opcion=opciones[url],
            rol=rol,
            defaults={
                'puede_consultar':  c,
                'puede_crear':      cr,
                'puede_actualizar': a,
                'puede_eliminar':   e,
            },
        )


def revertir_datos(apps, schema_editor):
    Menu    = apps.get_model('sigesi', 'Menu')
    Opcion  = apps.get_model('sigesi', 'Opcion')
    Permiso = apps.get_model('sigesi', 'Permiso')

    urls = [url for url, *_ in PERMISOS]
    Permiso.objects.filter(opcion__url__in=urls).delete()
    Opcion.objects.filter(url__in=[url for _, __, url in OPCIONES]).delete()
    Menu.objects.filter(nombre__in=[n for n, _ in MENUS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sigesi', '0002_restructura_menus_opciones_permisos'),
    ]

    operations = [
        migrations.RunPython(cargar_datos, revertir_datos),
    ]
