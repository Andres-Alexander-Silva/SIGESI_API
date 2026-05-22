"""Smoke tests for /api/v1/core/cronograma/ — CRUD, scope, aval gate, filters."""
from datetime import date

import pytest

from apps.sigesi.models import Cronograma, ActividadCronograma


URL = '/api/v1/core/cronograma/'


def _payload(plan_accion, **overrides):
    data = {
        'plan_accion': plan_accion.id,
        'descripcion': 'Cronograma semestral',
        'fecha_inicio': str(date.today()),
        'fecha_fin': str(date.today()),
        'cumplido': False,
    }
    data.update(overrides)
    return data


# --------------------------------------------------------------------------- #
# Happy paths per allowed role
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_admin_can_create_cronograma(auth_client, admin_user, plan_accion):
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(plan_accion), format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_director_grupo_can_create_cronograma(auth_client, director_grupo, plan_accion):
    client = auth_client(director_grupo)
    resp = client.post(URL, _payload(plan_accion), format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_director_semillero_can_create_cronograma(auth_client, director_semillero, plan_accion):
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(plan_accion), format='json')
    assert resp.status_code == 201, resp.content


# --------------------------------------------------------------------------- #
# Estudiante is read-only
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_estudiante_cannot_create_cronograma(auth_client, estudiante, plan_accion):
    client = auth_client(estudiante)
    resp = client.post(URL, _payload(plan_accion), format='json')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_estudiante_can_list_cronogramas_of_own_semillero(
    auth_client, estudiante, cronograma, semillero_aprobado
):
    from apps.sigesi.models import MatriculaSemillero
    MatriculaSemillero.objects.create(
        estudiante=estudiante, semillero=semillero_aprobado, semestre='2025-1')

    client = auth_client(estudiante)
    resp = client.get(URL)
    assert resp.status_code == 200, resp.content
    assert resp.json()['count'] == 1


# --------------------------------------------------------------------------- #
# Aval gate
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_create_cronograma_when_semillero_not_aprobado_returns_400(
    auth_client, director_semillero, plan_accion_sin_aval
):
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(plan_accion_sin_aval), format='json')
    assert resp.status_code == 400, resp.content


# --------------------------------------------------------------------------- #
# Filters
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_filter_by_semillero_and_semestre(
    auth_client, admin_user, cronograma, semillero_aprobado
):
    client = auth_client(admin_user)

    resp = client.get(f'{URL}?semillero={semillero_aprobado.id}')
    assert resp.status_code == 200
    assert resp.json()['count'] == 1

    resp = client.get(f'{URL}?semestre=2025-1')
    assert resp.status_code == 200
    assert resp.json()['count'] == 1

    resp = client.get(f'{URL}?semestre=2099-2')
    assert resp.status_code == 200
    assert resp.json()['count'] == 0


# --------------------------------------------------------------------------- #
# Row-level scope
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_director_semillero_does_not_see_other_semillero_cronogramas(
    auth_client, director_semillero, cronograma, grupo
):
    from apps.sigesi.models import Semillero, PlanAccion, User

    otro_director = User.objects.create(
        username='otrodir', cedula='CCOTRO1', roles=['director_semillero'],
        correo_personal='otrodir@example.com', email='otrodir@inst.edu',
    )
    otro_semillero = Semillero.objects.create(
        nombre='Otro', codigo='SOTRO', objetivo='o', fecha_creacion=date.today(),
        grupo_investigacion=grupo, director=otro_director,
        estado_aval=Semillero.EstadoAvalChoices.APROBADO,
    )
    otro_plan = PlanAccion.objects.create(
        semillero=otro_semillero, titulo='P', semestre='2025-1',
        objetivos='o', metas='m',
    )
    Cronograma.objects.create(
        plan_accion=otro_plan, fecha_inicio=date.today(), fecha_fin=date.today())

    client = auth_client(director_semillero)
    resp = client.get(URL)
    assert resp.status_code == 200
    assert resp.json()['count'] == 1


# --------------------------------------------------------------------------- #
# Nested actividades in read
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_retrieve_includes_nested_actividades(auth_client, admin_user, cronograma):
    ActividadCronograma.objects.create(
        cronograma=cronograma,
        titulo='Actividad uno',
        fecha_inicio=date.today(),
        fecha_fin_estimada=date.today(),
    )
    client = auth_client(admin_user)
    resp = client.get(f'{URL}{cronograma.id}/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert len(body['actividades']) == 1
    assert body['actividades'][0]['titulo'] == 'Actividad uno'
