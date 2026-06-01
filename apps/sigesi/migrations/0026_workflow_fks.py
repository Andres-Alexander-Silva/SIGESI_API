import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Esquema del flujo Evento → Convocatoria → Postulación → Participación.

    Corre después de 0025 (que vació Convocatoria en su propia transacción), de
    modo que añadir ``evento`` como FK no-nula es seguro: la tabla está vacía y
    no hay eventos de trigger pendientes.
    """

    dependencies = [
        ('sigesi', '0025_workflow_convocatoria_postulacion'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Liga la convocatoria a un evento (FK no-nula).
        migrations.AddField(
            model_name='convocatoria',
            name='evento',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='convocatorias',
                to='sigesi.evento',
                verbose_name='Evento',
            ),
        ),
        # 2. Auditoría de resolución de la postulación (aprobar/rechazar).
        migrations.AddField(
            model_name='postulacion',
            name='aprobado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='postulaciones_resueltas',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Resuelta por',
            ),
        ),
        migrations.AddField(
            model_name='postulacion',
            name='fecha_resolucion',
            field=models.DateTimeField(
                blank=True, null=True, verbose_name='Fecha de resolución'),
        ),
        # 3. Vincula la participación a la postulación aceptada que la habilitó.
        migrations.AddField(
            model_name='participacionevento',
            name='postulacion',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='participaciones',
                to='sigesi.postulacion',
                verbose_name='Postulación que respalda la participación',
            ),
        ),
    ]
