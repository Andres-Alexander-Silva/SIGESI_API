from django.db import migrations


def backfill(apps, schema_editor):
    """Asigna 'catedratico' a los directores de semillero sin tipo de vinculación.

    Los usuarios que ya tenían el rol ``director_semillero`` antes de existir el
    campo quedaron con ``tipo_vinculacion = null``. Se rellenan con el valor por
    defecto 'catedratico'. Solo se tocan los que están en ``null`` para no pisar
    valores ya ajustados manualmente (p. ej. 'planta').
    """
    User = apps.get_model('sigesi', 'User')
    User.objects.filter(
        roles__contains=['director_semillero'],
        tipo_vinculacion__isnull=True,
    ).update(tipo_vinculacion='catedratico')


class Migration(migrations.Migration):

    dependencies = [
        ('sigesi', '0022_user_tipo_vinculacion'),
    ]

    operations = [
        # Reversa noop: no revertimos para no perder valores ajustados a 'planta'.
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
