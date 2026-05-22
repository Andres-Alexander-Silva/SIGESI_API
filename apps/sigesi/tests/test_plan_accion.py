"""Smoke tests for /api/v1/core/plan-accion/ — CRUD, scope, aval gate, aprobar."""
import pytest
from django.utils import timezone

from apps.sigesi.models import PlanAccion, MatriculaSemillero


URL = '/api/v1/core/plan-accion/'


def _payload(semillero, semestre='2025-1', **overrides):
    data = {
        'semillero': semillero.id,
        'titulo': 'Plan semestral',
        'semestre': semestre,
        'objetivos': 'Objetivos del plan.',
        'metas': 'Metas del plan.',
    }
    data.update(overrides)
    return data


def _make_plan(semillero, semestre='2025-1', **overrides):
    return PlanAccion.objects.create(
        semillero=semillero,
        titulo='Plan',
        semestre=semestre,
        objetivos='o',
        metas='m',
        **overrides,
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
# Estudiante is read-only
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_estudiante_cannot_create_plan(auth_client, estudiante, semillero_aprobado):
    client = auth_client(estudiante)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_estudiante_can_list_plans_of_own_semillero(
    auth_client, estudiante, semillero_aprobado
):
    _make_plan(semillero_aprobado)
    MatriculaSemillero.objects.create(estudiante=estudiante, semillero=semillero_aprobado, semestre='2025-1')

    client = auth_client(estudiante)
    resp = client.get(URL)
    assert resp.status_code == 200, resp.content
    assert resp.json()['count'] == 1


# --------------------------------------------------------------------------- #
# Aval gate
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_create_plan_when_semillero_not_aprobado_returns_400(
    auth_client, director_semillero, semillero_sin_aprobar
):
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(semillero_sin_aprobar), format='json')
    assert resp.status_code == 400, resp.content


# --------------------------------------------------------------------------- #
# unique_together (semillero, semestre)
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_duplicate_semillero_semestre_returns_400(
    auth_client, admin_user, semillero_aprobado
):
    _make_plan(semillero_aprobado, semestre='2025-1')
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(semillero_aprobado, semestre='2025-1'), format='json')
    assert resp.status_code == 400, resp.content


# --------------------------------------------------------------------------- #
# Filters
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_filter_by_semillero_and_semestre(
    auth_client, admin_user, semillero_aprobado, semillero_sin_aprobar
):
    _make_plan(semillero_aprobado, semestre='2025-1')
    _make_plan(semillero_aprobado, semestre='2025-2')
    _make_plan(semillero_sin_aprobar, semestre='2025-1')

    client = auth_client(admin_user)

    resp = client.get(f'{URL}?semillero={semillero_aprobado.id}')
    assert resp.status_code == 200
    assert resp.json()['count'] == 2

    resp = client.get(f'{URL}?semillero={semillero_aprobado.id}&semestre=2025-2')
    assert resp.status_code == 200
    assert resp.json()['count'] == 1


# --------------------------------------------------------------------------- #
# Row-level scope
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_director_semillero_does_not_see_other_semillero_plans(
    auth_client, director_semillero, semillero_aprobado, grupo, lider_estudiantil
):
    from apps.sigesi.models import Semillero, User

    otro_director = User.objects.create(
        username='otrodir', cedula='CCOTRO1', roles=['director_semillero'],
        correo_personal='otrodir@example.com', email='otrodir@inst.edu',
    )
    otro_semillero = Semillero.objects.create(
        nombre='Otro', codigo='SOTRO', objetivo='o',
        fecha_creacion=semillero_aprobado.fecha_creacion,
        grupo_investigacion=grupo, director=otro_director,
        estado_aval=Semillero.EstadoAvalChoices.APROBADO,
    )
    _make_plan(semillero_aprobado)
    _make_plan(otro_semillero)

    client = auth_client(director_semillero)
    resp = client.get(URL)
    assert resp.status_code == 200
    assert resp.json()['count'] == 1


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
    assert plan.estado == PlanAccion.EstadoChoices.APROBADO
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
    assert plan.estado == PlanAccion.EstadoChoices.APROBADO
    assert plan.aprobado_por == director_grupo


@pytest.mark.django_db
def test_aprobar_already_aprobado_returns_400(auth_client, admin_user, semillero_aprobado):
    plan = _make_plan(semillero_aprobado, estado=PlanAccion.EstadoChoices.APROBADO)
    client = auth_client(admin_user)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_director_semillero_cannot_aprobar_plan(
    auth_client, director_semillero, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_semillero)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_aprobar_plan(
    auth_client, estudiante, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(estudiante)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    assert resp.status_code == 403, resp.content


# --------------------------------------------------------------------------- #
# estado transitions via PUT/PATCH
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_patch_estado_aprobado_stamps_like_aprobar(
    auth_client, director_grupo, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_grupo)
    resp = client.patch(f'{URL}{plan.id}/', {'estado': 'aprobado'}, format='json')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == PlanAccion.EstadoChoices.APROBADO
    assert plan.aprobado_por == director_grupo
    assert plan.fecha_aprobacion is not None


@pytest.mark.django_db
def test_admin_patch_estado_aprobado_stamps(auth_client, admin_user, semillero_aprobado):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(admin_user)
    resp = client.patch(f'{URL}{plan.id}/', {'estado': 'aprobado'}, format='json')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.aprobado_por == admin_user
    assert plan.fecha_aprobacion is not None


@pytest.mark.django_db
def test_director_semillero_cannot_set_estado_aprobado_via_patch(
    auth_client, director_semillero, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_semillero)
    resp = client.patch(f'{URL}{plan.id}/', {'estado': 'aprobado'}, format='json')
    assert resp.status_code == 403, resp.content

    plan.refresh_from_db()
    assert plan.aprobado_por is None


@pytest.mark.django_db
@pytest.mark.parametrize('estado', ['borrador', 'enviado', 'rechazado'])
def test_patch_estado_borrador_or_enviado_clears_aprobacion(
    auth_client, admin_user, semillero_aprobado, estado
):
    plan = _make_plan(
        semillero_aprobado,
        estado=PlanAccion.EstadoChoices.APROBADO,
        aprobado_por=admin_user,
    )
    client = auth_client(admin_user)
    resp = client.patch(f'{URL}{plan.id}/', {'estado': estado}, format='json')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == estado
    assert plan.aprobado_por is None
    assert plan.fecha_aprobacion is None


@pytest.mark.django_db
def test_patch_rechazado_without_prior_approval_clears_aprobacion(
    auth_client, admin_user, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)  # never approved
    client = auth_client(admin_user)
    resp = client.patch(f'{URL}{plan.id}/', {'estado': 'rechazado'}, format='json')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == PlanAccion.EstadoChoices.RECHAZADO
    assert plan.aprobado_por is None
    assert plan.fecha_aprobacion is None


@pytest.mark.django_db
@pytest.mark.parametrize('estado', ['en_ejecucion', 'finalizado'])
def test_patch_other_estado_requires_prior_approval(
    auth_client, admin_user, semillero_aprobado, estado
):
    plan = _make_plan(semillero_aprobado)  # never approved
    client = auth_client(admin_user)
    resp = client.patch(f'{URL}{plan.id}/', {'estado': estado}, format='json')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
@pytest.mark.parametrize('estado', ['en_ejecucion', 'finalizado'])
def test_patch_other_estado_allowed_when_previously_approved(
    auth_client, admin_user, semillero_aprobado, estado
):
    fecha = timezone.now()
    plan = _make_plan(
        semillero_aprobado,
        estado=PlanAccion.EstadoChoices.APROBADO,
        aprobado_por=admin_user,
        fecha_aprobacion=fecha,
    )
    client = auth_client(admin_user)
    resp = client.patch(f'{URL}{plan.id}/', {'estado': estado}, format='json')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == estado
    # El sello de aprobación se conserva.
    assert plan.aprobado_por == admin_user
    assert plan.fecha_aprobacion == fecha


@pytest.mark.django_db
def test_put_resending_aprobado_on_approved_plan_is_noop(
    auth_client, admin_user, semillero_aprobado
):
    fecha = timezone.now()
    plan = _make_plan(
        semillero_aprobado,
        estado=PlanAccion.EstadoChoices.APROBADO,
        aprobado_por=admin_user,
        fecha_aprobacion=fecha,
    )
    client = auth_client(admin_user)
    resp = client.put(f'{URL}{plan.id}/', {
        'semillero': semillero_aprobado.id,
        'titulo': 'Plan editado',
        'semestre': '2025-1',
        'objetivos': 'o2',
        'metas': 'm2',
        'estado': 'aprobado',
    }, format='json')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.titulo == 'Plan editado'
    assert plan.aprobado_por == admin_user
    assert plan.fecha_aprobacion == fecha  # no re-sello
