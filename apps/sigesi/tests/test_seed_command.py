"""Tests del comando de management ``seed_mock_data``."""
import pytest
from django.core.management import call_command

from apps.sigesi.models import (
    Proyecto, Semillero, ProduccionAcademica, MatriculaSemillero, User,
)

# Modelos contabilizados para verificar el umbral de ≥100 filas.
COUNTED_MODELS = [
    'ProgramaAcademico', 'LineaInvestigacion', 'Indicador', 'Convocatoria',
    'GrupoInvestigacion', 'Semillero', 'MatriculaSemillero', 'PlanEstrategico',
    'PlanAccion', 'Cronograma', 'ActividadCronograma', 'Proyecto',
    'EvaluacionProyecto', 'FaseProyecto',
    'HitoEntregable', 'Bitacora', 'Actividad', 'CronogramaProyecto', 'Evidencia',
    'Alerta', 'CompetenciaInvestigativa', 'Rubrica', 'Evaluacion',
    'PerfilInvestigativo', 'ProduccionAcademica', 'ParticipacionEvento',
    'Postulacion', 'MedicionIndicador', 'Informe',
]


def _total_rows():
    from apps.sigesi import models as m
    return sum(getattr(m, name).objects.count() for name in COUNTED_MODELS)


@pytest.mark.django_db
def test_seed_crea_al_menos_100_filas():
    call_command('seed_mock_data', '--seed', '7')
    assert _total_rows() >= 100


@pytest.mark.django_db
def test_seed_es_idempotente_sin_flush():
    call_command('seed_mock_data', '--seed', '7')
    total_1 = _total_rows()
    usuarios_1 = User.objects.count()

    call_command('seed_mock_data', '--seed', '7')
    # Re-ejecutar sin --flush no debe duplicar filas.
    assert _total_rows() == total_1
    assert User.objects.count() == usuarios_1


@pytest.mark.django_db
def test_flush_resetea_y_repuebla():
    call_command('seed_mock_data', '--seed', '1')
    primer_total = _total_rows()
    assert primer_total >= 100

    call_command('seed_mock_data', '--flush', '--seed', '1')
    assert _total_rows() >= 100
    # Solo se borran los usuarios mock (prefijo mock_).
    assert User.objects.filter(username__startswith='mock_').exists()


@pytest.mark.django_db
def test_flush_solo_borra_usuarios_mock():
    real = User.objects.create(
        username='persona_real', cedula='REAL01',
        correo_personal='real@example.com', email='real@ufps.edu.co',
        roles=['administrador'],
    )
    call_command('seed_mock_data', '--flush', '--seed', '1')
    assert User.objects.filter(pk=real.pk).exists()


@pytest.mark.django_db
def test_invariantes_de_datos_generados():
    call_command('seed_mock_data', '--seed', '3')

    # Egresados no conservan email institucional (invariante de User.save()).
    for u in User.objects.filter(is_graduated=True):
        assert u.email in (None, '')

    # Todo proyecto cuelga de al menos un semillero aprobado (gate de aval).
    aprobado = Semillero.EstadoAvalChoices.APROBADO
    for p in Proyecto.objects.all():
        assert p.semilleros.filter(estado_aval=aprobado).exists()

    # Toda producción académica tiene al menos un autor.
    for prod in ProduccionAcademica.objects.all():
        assert prod.autores.exists()

    # Las matrículas respetan unicidad (estudiante, semillero, semestre).
    claves = MatriculaSemillero.objects.values_list('estudiante', 'semillero', 'semestre')
    assert len(claves) == len(set(claves))
