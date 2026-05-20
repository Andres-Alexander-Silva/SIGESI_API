"""Smoke tests for /api/v1/core/dashboard/ and /proyectos/metricas-dashboard/."""
import pytest


DASHBOARD_URL = '/api/v1/core/dashboard/'
METRICS_URL = '/api/v1/core/proyectos/metricas-dashboard/'


# ---------------------------------------------------------------------------
# Global dashboard
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_admin_dashboard_returns_administrador_scope(auth_client, admin_user, proyecto):
    client = auth_client(admin_user)
    resp = client.get(DASHBOARD_URL)
    assert resp.status_code == 200
    body = resp.json()
    assert body['scope'] == 'administrador'
    assert 'proyectos_activos' in body


@pytest.mark.django_db
def test_estudiante_dashboard_returns_semillero_scope(auth_client, estudiante, proyecto):
    client = auth_client(estudiante)
    resp = client.get(DASHBOARD_URL)
    assert resp.status_code == 200
    assert resp.json()['scope'] == 'semillero'


@pytest.mark.django_db
def test_dashboard_scope_param_invalid_returns_400(auth_client, admin_user):
    client = auth_client(admin_user)
    resp = client.get(f'{DASHBOARD_URL}?scope=invalid')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_dashboard_scope_param_unauthorized_for_role_returns_400(
    auth_client, estudiante
):
    """Estudiante asking for admin scope should be rejected."""
    client = auth_client(estudiante)
    resp = client.get(f'{DASHBOARD_URL}?scope=administrador')
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Proyecto metrics dashboard
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_proyecto_metrics_returns_porcentaje_progreso_promedio(
    auth_client, admin_user, proyecto
):
    client = auth_client(admin_user)
    resp = client.get(METRICS_URL)
    assert resp.status_code == 200
    body = resp.json()
    assert 'scope_summary' in body
    assert 'porcentaje_progreso_promedio' in body['scope_summary']
    assert 'proyectos' in body


@pytest.mark.django_db
def test_proyecto_metrics_with_invalid_proyecto_id_returns_400(
    auth_client, admin_user
):
    client = auth_client(admin_user)
    resp = client.get(f'{METRICS_URL}?proyecto=notanint')
    assert resp.status_code == 400
