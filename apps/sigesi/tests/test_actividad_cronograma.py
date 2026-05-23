"""Smoke tests for /api/v1/core/actividad-cronograma/ — CRUD, scope, aval, dates."""
from datetime import date, timedelta

import pytest

from apps.sigesi.models import ActividadCronograma


URL = '/api/v1/core/actividad-cronograma/'


def _payload(cronograma, **overrides):
    hoy = date.today()
    data = {
        'cronograma': cronograma.id,
        'titulo': 'Actividad uno',
        'descripcion': 'desc',
        'objetivo_general': 'og',
        'objetivos_especificos': 'oe',
        'fecha_inicio': str(hoy),
        'fecha_fin_estimada': str(hoy + timedelta(days=10)),
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_director_semillero_can_create_actividad(auth_client, director_semillero, cronograma):
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(cronograma), format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_create_actividad(auth_client, estudiante, cronograma):
    client = auth_client(estudiante)
    resp = client.post(URL, _payload(cronograma), format='json')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_create_actividad_when_semillero_not_aprobado_returns_400(
    auth_client, director_semillero, plan_accion_sin_aval
):
    from apps.sigesi.models import Cronograma
    cron = Cronograma.objects.create(
        plan_accion=plan_accion_sin_aval, fecha_inicio=date.today(), fecha_fin=date.today())
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(cron), format='json')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_fecha_fin_estimada_before_inicio_returns_400(
    auth_client, director_semillero, cronograma
):
    hoy = date.today()
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(
        cronograma,
        fecha_inicio=str(hoy),
        fecha_fin_estimada=str(hoy - timedelta(days=1)),
    ), format='json')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_director_semillero_only_sees_own_actividades(
    auth_client, director_semillero, cronograma, grupo
):
    from apps.sigesi.models import Semillero, PlanAccion, Cronograma, User

    ActividadCronograma.objects.create(
        cronograma=cronograma, titulo='Mía',
        fecha_inicio=date.today(), fecha_fin_estimada=date.today())

    otro_director = User.objects.create(
        username='otrodir2', cedula='CCOTRO2', roles=['director_semillero'],
        correo_personal='otrodir2@example.com', email='otrodir2@inst.edu',
    )
    otro_semillero = Semillero.objects.create(
        nombre='Otro2', codigo='SOTRO2', objetivo='o', fecha_creacion=date.today(),
        grupo_investigacion=grupo, director=otro_director,
        estado_aval=Semillero.EstadoAvalChoices.APROBADO,
    )
    otro_plan = PlanAccion.objects.create(
        semillero=otro_semillero, titulo='P', semestre='2025-1', metas='m')
    otro_cron = Cronograma.objects.create(
        plan_accion=otro_plan, fecha_inicio=date.today(), fecha_fin=date.today())
    ActividadCronograma.objects.create(
        cronograma=otro_cron, titulo='Ajena',
        fecha_inicio=date.today(), fecha_fin_estimada=date.today())

    client = auth_client(director_semillero)
    resp = client.get(URL)
    assert resp.status_code == 200
    assert resp.json()['count'] == 1
