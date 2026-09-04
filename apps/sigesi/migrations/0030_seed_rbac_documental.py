"""Data migration: RBAC del modulo documental (HU-021).

Replica en un entorno ya desplegado lo que hace
``python manage.py seed_rbac`` (ver ese comando para el detalle y la
justificacion de cada permiso). Se mantiene autocontenida -sin importar
``apps.sigesi.models``- para no acoplar el historial de migraciones a
cambios futuros del comando, siguiendo el mismo patron que
``0003_data_menus_opciones_permisos.py``.
"""

from django.db import migrations

MENUS = [
    ('Producción y Evidencias', 'fa-folder-open'),
]

OPCIONES = [
    ('Producción y Evidencias', 'Avances', '/avances'),
    ('Producción y Evidencias', 'Producción Académica', '/produccion'),
    ('Producción y Evidencias', 'Participaciones en Eventos', '/participaciones_evento'),
    ('Producción y Evidencias', 'Eventos', '/eventos'),
    ('Producción y Evidencias', 'Proyectos', '/proyectos'),
    ('Producción y Evidencias', 'Actividades', '/actividades'),
]

PERMISOS = [
    ('/avances', 'administrador', True, True, True, True),
    ('/avances', 'director_grupo', True, True, True, True),
    ('/avances', 'director_semillero', True, True, True, True),
    ('/avances', 'lider_estudiantil', True, True, True, False),
    ('/avances', 'estudiante', True, True, True, False),

    ('/produccion', 'administrador', True, True, True, True),
    ('/produccion', 'director_grupo', True, True, True, True),
    ('/produccion', 'director_semillero', True, True, True, True),
    ('/produccion', 'lider_estudiantil', True, False, False, False),
    ('/produccion', 'estudiante', True, False, False, False),

    ('/participaciones_evento', 'administrador', True, True, True, True),
    ('/participaciones_evento', 'director_grupo', True, True, True, True),
    ('/participaciones_evento', 'director_semillero', True, True, True, True),
    ('/participaciones_evento', 'lider_estudiantil', True, True, True, True),
    ('/participaciones_evento', 'estudiante', True, False, False, False),

    ('/eventos', 'administrador', True, True, True, True),
    ('/eventos', 'director_grupo', True, True, True, True),
    ('/eventos', 'director_semillero', True, False, False, False),
    ('/eventos', 'lider_estudiantil', True, False, False, False),
    ('/eventos', 'estudiante', True, False, False, False),

    ('/proyectos', 'administrador', True, True, True, True),
    ('/proyectos', 'director_grupo', True, True, True, True),
    ('/proyectos', 'director_semillero', True, True, True, True),
    ('/proyectos', 'lider_estudiantil', True, True, True, False),
    ('/proyectos', 'estudiante', True, True, True, False),

    ('/actividades', 'administrador', True, True, True, True),
    ('/actividades', 'director_grupo', True, True, True, True),
    ('/actividades', 'director_semillero', True, True, True, True),
    ('/actividades', 'lider_estudiantil', True, True, True, True),
    ('/actividades', 'estudiante', True, False, False, False),
]


def cargar_datos(apps, schema_editor):
    Menu = apps.get_model('sigesi', 'Menu')
    Opcion = apps.get_model('sigesi', 'Opcion')
    Permiso = apps.get_model('sigesi', 'Permiso')

    menus = {}
    for nombre, icono in MENUS:
        obj, _ = Menu.objects.update_or_create(
            nombre=nombre, defaults={'icono': icono, 'estado': True},
        )
        menus[nombre] = obj

    opciones = {}
    for menu_nombre, nombre, url in OPCIONES:
        obj, _ = Opcion.objects.update_or_create(
            url=url,
            defaults={'menu': menus[menu_nombre], 'nombre': nombre, 'estado': True},
        )
        opciones[url] = obj

    for url, rol, consultar, crear, actualizar, eliminar in PERMISOS:
        Permiso.objects.update_or_create(
            opcion=opciones[url], rol=rol,
            defaults={
                'puede_consultar': consultar,
                'puede_crear': crear,
                'puede_actualizar': actualizar,
                'puede_eliminar': eliminar,
            },
        )

    # Limpieza de H1: la migracion 0003 sembro permisos para el rol 'comite',
    # que nunca existio en User.RolChoices ni se puede asignar a un usuario.
    roles_validos = {rol for _, rol, *_ in PERMISOS}
    Permiso.objects.exclude(rol__in=roles_validos).delete()


def revertir_datos(apps, schema_editor):
    Menu = apps.get_model('sigesi', 'Menu')
    Opcion = apps.get_model('sigesi', 'Opcion')
    Permiso = apps.get_model('sigesi', 'Permiso')

    urls = [url for _, __, url in OPCIONES]
    Permiso.objects.filter(opcion__url__in=urls).delete()
    Opcion.objects.filter(url__in=urls).delete()
    Menu.objects.filter(nombre__in=[n for n, _ in MENUS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sigesi', '0029_alter_informe_tipo'),
    ]

    operations = [
        migrations.RunPython(cargar_datos, revertir_datos),
    ]
