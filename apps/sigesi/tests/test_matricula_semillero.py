"""Smoke tests for /api/v1/core/inscripciones/ (MatriculaSemillero)."""
import pytest


URL = '/api/v1/core/inscripciones/'


@pytest.mark.django_db
def test_estudiante_inscribes_in_aprobado_semillero(
    auth_client, estudiante, semillero_aprobado
):
    client = auth_client(estudiante)
    resp = client.post(URL, {
        'estudiante': estudiante.id,
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_inscribe_in_sin_aprobar_semillero(
    auth_client, estudiante, semillero_sin_aprobar
):
    """Aval gate: writes against a non-approved semillero must fail for non-admin."""
    client = auth_client(estudiante)
    resp = client.post(URL, {
        'estudiante': estudiante.id,
        'semillero': semillero_sin_aprobar.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 400
    assert 'aval aprobado' in resp.content.decode().lower()


@pytest.mark.django_db
def test_admin_can_inscribe_in_sin_aprobar_semillero(
    auth_client, admin_user, otro_estudiante, semillero_sin_aprobar
):
    """Admin bypasses the aval gate."""
    client = auth_client(admin_user)
    resp = client.post(URL, {
        'estudiante': otro_estudiante.id,
        'semillero': semillero_sin_aprobar.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 201, resp.content
