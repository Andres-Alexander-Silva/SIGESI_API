"""Smoke tests for /api/v1/core/semilleros/ — CRUD + aval admin endpoint."""
from datetime import date

import pytest

from apps.sigesi.models import Semillero


URL = '/api/v1/core/semilleros/'


@pytest.mark.django_db
def test_admin_can_create_semillero(auth_client, admin_user, grupo, director_semillero):
    client = auth_client(admin_user)
    resp = client.post(URL, {
        'nombre': 'Semillero Nuevo',
        'codigo': 'SN1',
        'objetivo': 'Investigación.',
        'fecha_creacion': str(date.today()),
        'grupo_investigacion': grupo.id,
        'director': director_semillero.id,
    }, format='json')
    assert resp.status_code == 201, resp.content
    # Default aval is sin_aprobar — admin still has to approve via /aval/
    new = Semillero.objects.get(codigo='SN1')
    assert new.estado_aval == Semillero.EstadoAvalChoices.SIN_APROBAR


@pytest.mark.django_db
def test_director_cannot_change_estado_aval_via_regular_patch(
    auth_client, director_semillero, semillero_sin_aprobar
):
    """Aval fields are not in SemilleroCreateUpdateSerializer.fields."""
    client = auth_client(director_semillero)
    resp = client.patch(
        f'{URL}{semillero_sin_aprobar.id}/',
        {'estado_aval': 'aprobado'},
        format='json',
    )
    # Request may succeed (200) — the field is silently ignored, not rejected.
    assert resp.status_code in (200, 400)
    semillero_sin_aprobar.refresh_from_db()
    assert semillero_sin_aprobar.estado_aval == Semillero.EstadoAvalChoices.SIN_APROBAR


@pytest.mark.django_db
def test_aval_get_returns_state_for_any_authenticated(
    auth_client, estudiante, semillero_aprobado
):
    client = auth_client(estudiante)
    resp = client.get(f'{URL}{semillero_aprobado.id}/aval/')
    assert resp.status_code == 200
    assert resp.json()['estado_aval'] == 'aprobado'


@pytest.mark.django_db
def test_admin_aval_patch_to_aprobado_stamps_user_and_date(
    auth_client, admin_user, semillero_sin_aprobar
):
    client = auth_client(admin_user)
    resp = client.patch(
        f'{URL}{semillero_sin_aprobar.id}/aval/',
        {'estado_aval': 'aprobado', 'tipo_documento': 'acta', 'numero_acta': '0042'},
        format='json',
    )
    assert resp.status_code == 200, resp.content

    semillero_sin_aprobar.refresh_from_db()
    assert semillero_sin_aprobar.estado_aval == Semillero.EstadoAvalChoices.APROBADO
    assert semillero_sin_aprobar.usuario_aprobacion_id == admin_user.id
    assert semillero_sin_aprobar.fecha_aprobacion is not None


@pytest.mark.django_db
def test_admin_aval_patch_to_aprobado_without_required_docs_returns_400(
    auth_client, admin_user, semillero_sin_aprobar
):
    client = auth_client(admin_user)
    resp = client.patch(
        f'{URL}{semillero_sin_aprobar.id}/aval/',
        {'estado_aval': 'aprobado'},
        format='json',
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_aval_patch_as_non_admin_returns_403(
    auth_client, director_semillero, semillero_sin_aprobar
):
    client = auth_client(director_semillero)
    resp = client.patch(
        f'{URL}{semillero_sin_aprobar.id}/aval/',
        {'estado_aval': 'aprobado', 'tipo_documento': 'acta', 'numero_acta': '0001'},
        format='json',
    )
    assert resp.status_code == 403
