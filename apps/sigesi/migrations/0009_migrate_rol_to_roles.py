"""
Data migration: copia el valor de 'rol' (CharField) a 'roles' (ArrayField).
Cada usuario existente tendrá su rol actual como un array de un elemento.
"""
from django.db import migrations


def forwards_migrate_rol_to_roles(apps, schema_editor):
    """Convierte el valor singular 'rol' al array 'roles'."""
    User = apps.get_model('sigesi', 'User')
    for user in User.objects.all():
        if user.rol:
            user.roles = [user.rol]
        else:
            user.roles = ['estudiante']
        user.save(update_fields=['roles'])


def backwards_migrate_roles_to_rol(apps, schema_editor):
    """Revierte el array 'roles' al valor singular 'rol' (toma el primero)."""
    User = apps.get_model('sigesi', 'User')
    for user in User.objects.all():
        user.rol = user.roles[0] if user.roles else 'estudiante'
        user.save(update_fields=['rol'])


class Migration(migrations.Migration):

    dependencies = [
        ('sigesi', '0008_user_add_roles_arrayfield'),
    ]

    operations = [
        migrations.RunPython(
            forwards_migrate_rol_to_roles,
            backwards_migrate_roles_to_rol,
        ),
    ]
