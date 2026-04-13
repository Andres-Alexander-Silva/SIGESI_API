"""
Data migration: carga inicial de Menús, Opciones y Permisos por rol.

Estructura de menús:
  1. Dashboard
  2. Semilleros
  3. Grupos de Investigación
  4. Convocatorias
  5. Reportes
  6. Configuración  (solo administrador)

Roles:
  administrador, director_grupo, director_semillero,
  lider_estudiantil, estudiante, comite
"""

from django.db import migrations


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

MENUS = [
    # (nombre, icono, orden, url)
    ("Dashboard",               "fa-gauge",         1,  "/dashboard"),
    ("Semilleros",              "fa-flask",         2,  "/semilleros"),
    ("Grupos de Investigación", "fa-users",         3,  "/grupos"),
    ("Convocatorias",           "fa-bullhorn",      4,  "/convocatorias"),
    ("Reportes",                "fa-chart-bar",     5,  "/reportes"),
    ("Configuración",           "fa-gear",          6,  "/configuracion"),
]

# (menu_nombre, nombre_opcion, codigo, accion, descripcion)
OPCIONES = [
    # Dashboard
    ("Dashboard", "Ver dashboard",          "dashboard.ver",            "ver",      "Visualizar el panel principal"),

    # Semilleros
    ("Semilleros", "Ver semilleros",        "semilleros.ver",           "ver",      "Listar y consultar semilleros"),
    ("Semilleros", "Crear semillero",       "semilleros.crear",         "crear",    "Registrar un nuevo semillero"),
    ("Semilleros", "Editar semillero",      "semilleros.editar",        "editar",   "Modificar datos de un semillero"),
    ("Semilleros", "Eliminar semillero",    "semilleros.eliminar",      "eliminar", "Dar de baja un semillero"),
    ("Semilleros", "Aprobar semillero",     "semilleros.aprobar",       "aprobar",  "Aprobar o rechazar un semillero"),
    ("Semilleros", "Exportar semilleros",   "semilleros.exportar",      "exportar", "Exportar listado de semilleros"),

    # Grupos de Investigación
    ("Grupos de Investigación", "Ver grupos",       "grupos.ver",       "ver",      "Listar y consultar grupos"),
    ("Grupos de Investigación", "Crear grupo",      "grupos.crear",     "crear",    "Registrar un nuevo grupo"),
    ("Grupos de Investigación", "Editar grupo",     "grupos.editar",    "editar",   "Modificar datos de un grupo"),
    ("Grupos de Investigación", "Eliminar grupo",   "grupos.eliminar",  "eliminar", "Dar de baja un grupo"),
    ("Grupos de Investigación", "Exportar grupos",  "grupos.exportar",  "exportar", "Exportar listado de grupos"),

    # Convocatorias
    ("Convocatorias", "Ver convocatorias",       "convocatorias.ver",        "ver",      "Listar convocatorias"),
    ("Convocatorias", "Crear convocatoria",      "convocatorias.crear",      "crear",    "Publicar nueva convocatoria"),
    ("Convocatorias", "Editar convocatoria",     "convocatorias.editar",     "editar",   "Modificar una convocatoria"),
    ("Convocatorias", "Eliminar convocatoria",   "convocatorias.eliminar",   "eliminar", "Eliminar una convocatoria"),
    ("Convocatorias", "Aprobar convocatoria",    "convocatorias.aprobar",    "aprobar",  "Aprobar o rechazar convocatoria"),

    # Reportes
    ("Reportes", "Ver reportes",        "reportes.ver",         "ver",      "Consultar reportes del sistema"),
    ("Reportes", "Exportar reportes",   "reportes.exportar",    "exportar", "Descargar reportes en PDF/Excel"),

    # Configuración
    ("Configuración", "Ver usuarios",       "config.usuarios.ver",      "ver",      "Listar usuarios del sistema"),
    ("Configuración", "Crear usuario",      "config.usuarios.crear",    "crear",    "Registrar nuevo usuario"),
    ("Configuración", "Editar usuario",     "config.usuarios.editar",   "editar",   "Modificar datos de usuario"),
    ("Configuración", "Eliminar usuario",   "config.usuarios.eliminar", "eliminar", "Eliminar usuario del sistema"),
    ("Configuración", "Ver menús",          "config.menus.ver",         "ver",      "Listar menús del sistema"),
    ("Configuración", "Crear menú",         "config.menus.crear",       "crear",    "Registrar nuevo menú"),
    ("Configuración", "Editar menú",        "config.menus.editar",      "editar",   "Modificar un menú"),
    ("Configuración", "Eliminar menú",      "config.menus.eliminar",    "eliminar", "Eliminar un menú"),
    ("Configuración", "Ver permisos",       "config.permisos.ver",      "ver",      "Consultar permisos por rol"),
    ("Configuración", "Gestionar permisos", "config.permisos.editar",   "editar",   "Asignar o revocar permisos"),
]

# (codigo_opcion, rol, permitido)
PERMISOS = [
    # ── ADMINISTRADOR: acceso total ──────────────────────────────────────────
    ("dashboard.ver",               "administrador", True),

    ("semilleros.ver",              "administrador", True),
    ("semilleros.crear",            "administrador", True),
    ("semilleros.editar",           "administrador", True),
    ("semilleros.eliminar",         "administrador", True),
    ("semilleros.aprobar",          "administrador", True),
    ("semilleros.exportar",         "administrador", True),

    ("grupos.ver",                  "administrador", True),
    ("grupos.crear",                "administrador", True),
    ("grupos.editar",               "administrador", True),
    ("grupos.eliminar",             "administrador", True),
    ("grupos.exportar",             "administrador", True),

    ("convocatorias.ver",           "administrador", True),
    ("convocatorias.crear",         "administrador", True),
    ("convocatorias.editar",        "administrador", True),
    ("convocatorias.eliminar",      "administrador", True),
    ("convocatorias.aprobar",       "administrador", True),

    ("reportes.ver",                "administrador", True),
    ("reportes.exportar",           "administrador", True),

    ("config.usuarios.ver",         "administrador", True),
    ("config.usuarios.crear",       "administrador", True),
    ("config.usuarios.editar",      "administrador", True),
    ("config.usuarios.eliminar",    "administrador", True),
    ("config.menus.ver",            "administrador", True),
    ("config.menus.crear",          "administrador", True),
    ("config.menus.editar",         "administrador", True),
    ("config.menus.eliminar",       "administrador", True),
    ("config.permisos.ver",         "administrador", True),
    ("config.permisos.editar",      "administrador", True),

    # ── COMITÉ DE INVESTIGACIÓN ──────────────────────────────────────────────
    ("dashboard.ver",               "comite", True),
    ("semilleros.ver",              "comite", True),
    ("semilleros.aprobar",          "comite", True),
    ("semilleros.exportar",         "comite", True),
    ("grupos.ver",                  "comite", True),
    ("grupos.exportar",             "comite", True),
    ("convocatorias.ver",           "comite", True),
    ("convocatorias.crear",         "comite", True),
    ("convocatorias.editar",        "comite", True),
    ("convocatorias.aprobar",       "comite", True),
    ("reportes.ver",                "comite", True),
    ("reportes.exportar",           "comite", True),

    # ── DIRECTOR DE GRUPO ────────────────────────────────────────────────────
    ("dashboard.ver",               "director_grupo", True),
    ("semilleros.ver",              "director_grupo", True),
    ("semilleros.crear",            "director_grupo", True),
    ("semilleros.editar",           "director_grupo", True),
    ("semilleros.exportar",         "director_grupo", True),
    ("grupos.ver",                  "director_grupo", True),
    ("grupos.editar",               "director_grupo", True),
    ("grupos.exportar",             "director_grupo", True),
    ("convocatorias.ver",           "director_grupo", True),
    ("convocatorias.crear",         "director_grupo", True),
    ("convocatorias.editar",        "director_grupo", True),
    ("reportes.ver",                "director_grupo", True),
    ("reportes.exportar",           "director_grupo", True),

    # ── DIRECTOR DE SEMILLERO ────────────────────────────────────────────────
    ("dashboard.ver",               "director_semillero", True),
    ("semilleros.ver",              "director_semillero", True),
    ("semilleros.editar",           "director_semillero", True),
    ("semilleros.exportar",         "director_semillero", True),
    ("grupos.ver",                  "director_semillero", True),
    ("convocatorias.ver",           "director_semillero", True),
    ("reportes.ver",                "director_semillero", True),

    # ── LÍDER ESTUDIANTIL ────────────────────────────────────────────────────
    ("dashboard.ver",               "lider_estudiantil", True),
    ("semilleros.ver",              "lider_estudiantil", True),
    ("grupos.ver",                  "lider_estudiantil", True),
    ("convocatorias.ver",           "lider_estudiantil", True),
    ("reportes.ver",                "lider_estudiantil", True),

    # ── ESTUDIANTE ───────────────────────────────────────────────────────────
    ("dashboard.ver",               "estudiante", True),
    ("semilleros.ver",              "estudiante", True),
    ("grupos.ver",                  "estudiante", True),
    ("convocatorias.ver",           "estudiante", True),
]


# ---------------------------------------------------------------------------
# Funciones de migración
# ---------------------------------------------------------------------------

def cargar_datos(apps, schema_editor):
    Menu    = apps.get_model('sigesi', 'Menu')
    Opcion  = apps.get_model('sigesi', 'Opcion')
    Permiso = apps.get_model('sigesi', 'Permiso')

    # 1. Menús
    menus = {}
    for nombre, icono, orden, url in MENUS:
        menu, _ = Menu.objects.get_or_create(
            nombre=nombre,
            defaults={'icono': icono, 'orden': orden, 'url': url, 'is_active': True},
        )
        menus[nombre] = menu

    # 2. Opciones
    opciones = {}
    for menu_nombre, nombre, codigo, accion, descripcion in OPCIONES:
        opcion, _ = Opcion.objects.get_or_create(
            codigo=codigo,
            defaults={
                'menu': menus[menu_nombre],
                'nombre': nombre,
                'accion': accion,
                'descripcion': descripcion,
                'is_active': True,
            },
        )
        opciones[codigo] = opcion

    # 3. Permisos
    for codigo, rol, permitido in PERMISOS:
        Permiso.objects.get_or_create(
            opcion=opciones[codigo],
            rol=rol,
            defaults={'permitido': permitido},
        )


def revertir_datos(apps, schema_editor):
    Menu    = apps.get_model('sigesi', 'Menu')
    Opcion  = apps.get_model('sigesi', 'Opcion')
    Permiso = apps.get_model('sigesi', 'Permiso')

    codigos = [c for c, _, _ in PERMISOS]
    Permiso.objects.filter(opcion__codigo__in=codigos).delete()
    Opcion.objects.filter(codigo__in=codigos).delete()
    Menu.objects.filter(nombre__in=[m[0] for m in MENUS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sigesi', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(cargar_datos, revertir_datos),
    ]
