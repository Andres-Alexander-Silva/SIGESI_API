from django.db import migrations


def borrar_convocatorias(apps, schema_editor):
    """Vacía Convocatoria antes de convertir ``evento`` en FK no-nula.

    Las convocatorias previas no tenían evento asociado; al pasar a una FK
    no-nula hacia ``Evento`` no hay forma de mapearlas automáticamente, por lo
    que se descartan (decisión: wipe & recreate sobre datos de desarrollo). El
    borrado se propaga en cascada a sus Postulaciones.

    El borrado vive en su **propia** migración (separada del ``ALTER TABLE`` de
    0026) porque PostgreSQL no permite alterar una tabla con eventos de trigger
    pendientes dentro de la misma transacción: una migración atómica que borrara
    y luego alterara la misma tabla fallaría con ``ObjectInUse``.
    """
    apps.get_model('sigesi', 'Convocatoria').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sigesi', '0024_evento_participacionevento_fk'),
    ]

    operations = [
        migrations.RunPython(borrar_convocatorias, migrations.RunPython.noop),
    ]
