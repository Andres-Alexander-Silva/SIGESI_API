from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sigesi', '0020_actividadcronograma_estado'),
    ]

    operations = [
        migrations.AlterField(
            model_name='evaluacion',
            name='nivel_alcanzado',
            field=models.CharField(
                blank=True,
                choices=[
                    ('basico', 'Básico'),
                    ('intermedio', 'Intermedio'),
                    ('avanzado', 'Avanzado'),
                ],
                max_length=20,
                null=True,
                verbose_name='Nivel alcanzado',
            ),
        ),
    ]
