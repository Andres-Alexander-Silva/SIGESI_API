import django.db.models.deletion
from django.db import migrations, models


def borrar_participaciones(apps, schema_editor):
    """Vacía ParticipacionEvento antes de convertir ``evento`` en FK.

    Las filas previas guardaban el evento como texto libre; al pasar a una FK
    no-nula hacia ``Evento`` no hay forma de mapearlas automáticamente, por lo
    que se descartan (decisión: wipe & recreate sobre datos de desarrollo).
    """
    apps.get_model('sigesi', 'ParticipacionEvento').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sigesi', '0023_backfill_tipo_vinculacion'),
    ]

    operations = [
        # 1. Descarta las participaciones existentes (evento era texto libre).
        migrations.RunPython(borrar_participaciones, migrations.RunPython.noop),
        # 2. Nuevo modelo Evento.
        migrations.CreateModel(
            name='Evento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=300, verbose_name='Nombre del evento')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('modalidad', models.CharField(choices=[('presencial', 'Presencial'), ('virtual', 'Virtual'), ('hibrido', 'Híbrido')], default='presencial', max_length=20, verbose_name='Modalidad')),
                ('lugar', models.CharField(blank=True, max_length=200, verbose_name='Lugar')),
                ('fecha_inicio', models.DateField(verbose_name='Fecha de inicio')),
                ('fecha_fin', models.DateField(blank=True, null=True, verbose_name='Fecha de fin')),
                ('estado', models.CharField(choices=[('activo', 'Activo'), ('finalizado', 'Finalizado'), ('cancelado', 'Cancelado')], default='activo', max_length=20, verbose_name='Estado')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Evento',
                'verbose_name_plural': 'Eventos',
                'ordering': ['-fecha_inicio'],
            },
        ),
        # 3. Quita los campos que ahora viven en Evento (y el evento de texto).
        migrations.RemoveField(model_name='participacionevento', name='evento'),
        migrations.RemoveField(model_name='participacionevento', name='lugar'),
        migrations.RemoveField(model_name='participacionevento', name='fecha_inicio'),
        migrations.RemoveField(model_name='participacionevento', name='fecha_fin'),
        # 4. Reintroduce ``evento`` como FK no-nula hacia Evento.
        migrations.AddField(
            model_name='participacionevento',
            name='evento',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='participaciones',
                to='sigesi.evento',
                verbose_name='Evento',
            ),
        ),
        # 5. Nuevo orden y unicidad (un participante, una vez por evento).
        migrations.AlterModelOptions(
            name='participacionevento',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Participación en Evento',
                'verbose_name_plural': 'Participaciones en Eventos',
            },
        ),
        migrations.AlterUniqueTogether(
            name='participacionevento',
            unique_together={('participante', 'evento')},
        ),
    ]
