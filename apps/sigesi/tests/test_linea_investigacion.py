"""Smoke tests for /api/v1/core/lineas-investigacion/.

The current ViewSet uses IsAuthenticated only — any authenticated user can write.
This test documents that behavior so a regression that tightens it is caught.
"""
import pytest


URL = '/api/v1/core/lineas-investigacion/'


@pytest.mark.django_db
def test_authenticated_user_can_create_linea(auth_client, director_semillero):
    client = auth_client(director_semillero)
    resp = client.post(URL, {
        'nombre': 'Robótica',
        'descripcion': 'Aplicada',
        'is_active': True,
    }, format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_unauthenticated_cannot_access(api_client):
    resp = api_client.get(URL)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_estudiante_can_list_lineas(auth_client, estudiante, linea):
    client = auth_client(estudiante)
    resp = client.get(URL)
    assert resp.status_code == 200
