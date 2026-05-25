"""Smoke tests for /api/v1/core/plan-estrategico/ — CRUD, scope, business rules.

Cubre: happy-path por rol permitido, 403 de roles de solo lectura, filtro de
alcance por rol, regla de un plan por semillero/año, restricción del cambio de
``estado`` a Admin/Director de Grupo, y la forma anidada del semillero en lectura.
"""
from datetime import date

import pytest

from apps.sigesi.models import (
    GrupoInvestigacion,
    PlanEstrategico,
    ProgramaAcademico,
    Semillero,
)


URL = '/api/v1/core/plan-estrategico/'


def _payload(semillero, anio=2025, **overrides):
    data = {
        'semillero': semillero.id,
        'titulo': 'Plan estratégico anual',
        'anio': anio,
        'objetivos': 'Objetivos del plan.',
        'metas': 'Metas del plan.',
        'indicadores': 'Indicadores del plan.',
    }
    data.update(overrides)
    return data


def _make_plan(semillero, anio=2025, **overrides):
    return PlanEstrategico.objects.create(
        semillero=semillero,
        titulo='Plan',
        anio=anio,
        objetivos='o',
        metas='m',
        indicadores='i',
        **overrides,
    )


def _filas(resp):
    """Devuelve las filas de la respuesta, sea paginada o no."""
    data = resp.data
    return data['results'] if isinstance(data, dict) and 'results' in data else data


@pytest.fixture
def semillero_otro_grupo(db, programa):
    """Semillero de un grupo cuyo director NO es el fixture ``director_grupo``."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    n = User.objects.count() + 1
    otro_director = User.objects.create(
        username=f'otro{n}',
        cedula=f'CC9{n:05d}',
        correo_personal=f'otro{n}@example.com',
        email=f'otro{n}@inst.edu',
        first_name=f'Otro{n}',
        last_name='Director',
        roles=['director_grupo'],
        is_active=True,
    )
    otro_director.set_password('x')
    otro_director.save()
    grupo = GrupoInvestigacion.objects.create(
        nombre='Grupo Omega',
        codigo='G9',
        fecha_creacion=date.today(),
        programa_academico=programa,
        director=otro_director,
    )
    return Semillero.objects.create(
        nombre='Semillero Delta',
        codigo='S9',
        objetivo='Otro grupo.',
        fecha_creacion=date.today(),
        grupo_investigacion=grupo,
        director=otro_director,
        estado_aval=Semillero.EstadoAvalChoices.APROBADO,
    )


# --------------------------------------------------------------------------- #
# Happy paths per allowed role
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_admin_can_create_plan(auth_client, admin_user, semillero_aprobado):
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_director_grupo_can_create_plan(auth_client, director_grupo, semillero_aprobado):
    client = auth_client(director_grupo)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_director_semillero_can_create_plan(auth_client, director_semillero, semillero_aprobado):
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 201, resp.content


# --------------------------------------------------------------------------- #
# Estudiante / Líder Estudiantil are read-only
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_estudiante_cannot_create_plan(auth_client, estudiante, semillero_aprobado):
    client = auth_client(estudiante)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_lider_cannot_create_plan(auth_client, lider_estudiantil, semillero_aprobado):
    client = auth_client(lider_estudiantil)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_estudiante_can_read_plan(auth_client, estudiante, semillero_aprobado):
    _make_plan(semillero_aprobado)
    client = auth_client(estudiante)
    resp = client.get(URL)
    assert resp.status_code == 200, resp.content


# --------------------------------------------------------------------------- #
# Scope filter per role
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_director_grupo_only_sees_own_group(auth_client, director_grupo,
                                             semillero_aprobado, semillero_otro_grupo):
    _make_plan(semillero_aprobado, anio=2025)
    _make_plan(semillero_otro_grupo, anio=2025)
    client = auth_client(director_grupo)
    resp = client.get(URL)
    assert resp.status_code == 200
    ids = {row['semillero']['id'] for row in _filas(resp)}
    assert semillero_aprobado.id in ids
    assert semillero_otro_grupo.id not in ids


# --------------------------------------------------------------------------- #
# Business rule: one plan per (semillero, anio)
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_unique_plan_per_year(auth_client, admin_user, semillero_aprobado):
    _make_plan(semillero_aprobado, anio=2025)
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(semillero_aprobado, anio=2025), format='json')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_same_semillero_different_year_ok(auth_client, admin_user, semillero_aprobado):
    _make_plan(semillero_aprobado, anio=2025)
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(semillero_aprobado, anio=2026), format='json')
    assert resp.status_code == 201, resp.content


# --------------------------------------------------------------------------- #
# Business rule: only Admin / Director de Grupo can change estado
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_director_semillero_cannot_change_estado(auth_client, director_semillero, semillero_aprobado):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_semillero)
    resp = client.patch(
        f'{URL}{plan.id}/',
        {'estado': PlanEstrategico.EstadoChoices.APROBADO},
        format='json',
    )
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_director_semillero_can_edit_other_fields(auth_client, director_semillero, semillero_aprobado):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_semillero)
    resp = client.patch(f'{URL}{plan.id}/', {'titulo': 'Nuevo título'}, format='json')
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
def test_director_grupo_can_change_estado(auth_client, director_grupo, semillero_aprobado):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_grupo)
    resp = client.patch(
        f'{URL}{plan.id}/',
        {'estado': PlanEstrategico.EstadoChoices.APROBADO},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    plan.refresh_from_db()
    assert plan.estado == PlanEstrategico.EstadoChoices.APROBADO


@pytest.mark.django_db
def test_admin_can_change_estado(auth_client, admin_user, semillero_aprobado):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(admin_user)
    resp = client.patch(
        f'{URL}{plan.id}/',
        {'estado': PlanEstrategico.EstadoChoices.APROBADO},
        format='json',
    )
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
def test_director_grupo_cannot_touch_other_group_plan(auth_client, director_grupo, semillero_otro_grupo):
    plan = _make_plan(semillero_otro_grupo)
    client = auth_client(director_grupo)
    resp = client.patch(
        f'{URL}{plan.id}/',
        {'estado': PlanEstrategico.EstadoChoices.APROBADO},
        format='json',
    )
    # El plan queda fuera del queryset del director de grupo -> 404.
    assert resp.status_code == 404, resp.content


# --------------------------------------------------------------------------- #
# Read shape: semillero is nested
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_retrieve_embeds_semillero(auth_client, admin_user, semillero_aprobado):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(admin_user)
    resp = client.get(f'{URL}{plan.id}/')
    assert resp.status_code == 200, resp.content
    assert isinstance(resp.data['semillero'], dict)
    assert resp.data['semillero']['id'] == semillero_aprobado.id
    assert resp.data['semillero']['nombre'] == semillero_aprobado.nombre


# --------------------------------------------------------------------------- #
# aprobar action
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_admin_can_aprobar_plan(auth_client, admin_user, semillero_aprobado):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(admin_user)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == PlanEstrategico.EstadoChoices.APROBADO
    assert plan.aprobado_por == admin_user
    assert plan.fecha_aprobacion is not None


@pytest.mark.django_db
def test_director_grupo_can_aprobar_plan_of_own_group(
    auth_client, director_grupo, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_grupo)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == PlanEstrategico.EstadoChoices.APROBADO
    assert plan.aprobado_por == director_grupo


@pytest.mark.django_db
def test_aprobar_already_aprobado_returns_400(auth_client, admin_user, semillero_aprobado):
    plan = _make_plan(semillero_aprobado, estado=PlanEstrategico.EstadoChoices.APROBADO)
    client = auth_client(admin_user)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_director_grupo_cannot_aprobar_other_group_plan(
    auth_client, director_grupo, semillero_otro_grupo
):
    plan = _make_plan(semillero_otro_grupo)
    client = auth_client(director_grupo)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    # El plan queda fuera del queryset del director de grupo -> 404.
    assert resp.status_code == 404, resp.content


@pytest.mark.django_db
def test_director_semillero_cannot_aprobar_plan(
    auth_client, director_semillero, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_semillero)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_lider_cannot_aprobar_plan(auth_client, lider_estudiantil, semillero_aprobado):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(lider_estudiantil)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_aprobar_plan(auth_client, estudiante, semillero_aprobado):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(estudiante)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    assert resp.status_code == 403, resp.content


# --------------------------------------------------------------------------- #
# rechazar action
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_admin_can_rechazar_plan(auth_client, admin_user, semillero_aprobado):
    plan = _make_plan(
        semillero_aprobado,
        estado=PlanEstrategico.EstadoChoices.APROBADO,
        aprobado_por=admin_user,
    )
    client = auth_client(admin_user)
    resp = client.post(f'{URL}{plan.id}/rechazar/')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == PlanEstrategico.EstadoChoices.RECHAZADO
    assert plan.aprobado_por is None
    assert plan.fecha_aprobacion is None


@pytest.mark.django_db
def test_director_grupo_can_rechazar_plan_of_own_group(
    auth_client, director_grupo, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_grupo)
    resp = client.post(f'{URL}{plan.id}/rechazar/')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == PlanEstrategico.EstadoChoices.RECHAZADO


@pytest.mark.django_db
def test_rechazar_already_rechazado_returns_400(auth_client, admin_user, semillero_aprobado):
    plan = _make_plan(semillero_aprobado, estado=PlanEstrategico.EstadoChoices.RECHAZADO)
    client = auth_client(admin_user)
    resp = client.post(f'{URL}{plan.id}/rechazar/')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_director_grupo_cannot_rechazar_other_group_plan(
    auth_client, director_grupo, semillero_otro_grupo
):
    plan = _make_plan(semillero_otro_grupo)
    client = auth_client(director_grupo)
    resp = client.post(f'{URL}{plan.id}/rechazar/')
    # El plan queda fuera del queryset del director de grupo -> 404.
    assert resp.status_code == 404, resp.content


@pytest.mark.django_db
def test_director_semillero_cannot_rechazar_plan(
    auth_client, director_semillero, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_semillero)
    resp = client.post(f'{URL}{plan.id}/rechazar/')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_lider_cannot_rechazar_plan(auth_client, lider_estudiantil, semillero_aprobado):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(lider_estudiantil)
    resp = client.post(f'{URL}{plan.id}/rechazar/')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_rechazar_plan(auth_client, estudiante, semillero_aprobado):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(estudiante)
    resp = client.post(f'{URL}{plan.id}/rechazar/')
    assert resp.status_code == 403, resp.content
