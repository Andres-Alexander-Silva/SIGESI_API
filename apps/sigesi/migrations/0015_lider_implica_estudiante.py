"""
Data migration: garantiza el invariante "todo líder estudiantil es también
estudiante". Agrega el rol 'estudiante' a los usuarios que tienen
'lider_estudiantil' pero no 'estudiante' en su array de roles.
"""
from django.db import migrations


def forwards_lider_implica_estudiante(apps, schema_editor):
    User = apps.get_model('sigesi', 'User')
    for user in User.objects.filter(roles__contains=['lider_estudiantil']).iterator():
        if 'estudiante' not in user.roles:
            user.roles = list(user.roles) + ['estudiante']
            user.save(update_fields=['roles'])


class Migration(migrations.Migration):

    dependencies = [
        ('sigesi', '0014_lineainvestigacion_mision_lineainvestigacion_vision'),
    ]

    operations = [
        migrations.RunPython(
            forwards_lider_implica_estudiante,
            migrations.RunPython.noop,
        ),
    ]
