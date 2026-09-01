"""Smoke tests for /api/v1/core/lineas-investigacion/.

The ViewSet uses AdminOrReadOnlyPermission: lectura abierta a cualquier
autenticado, escritura reservada al administrador.
"""
import pytest


URL = '/api/v1/core/lineas-investigacion/'


@pytest.mark.django_db
def test_admin_can_create_linea(auth_client, admin_user):
    client = auth_client(admin_user)
    resp = client.post(URL, {
        'nombre': 'Robótica',
        'descripcion': 'Aplicada',
        'mision': 'Desarrollar prototipos robóticos innovadores.',
        'vision': 'Ser líderes nacionales en investigación de robótica aplicada.',
        'is_active': True,
    }, format='json')
    assert resp.status_code == 201, resp.content
    data = resp.json()
    assert data['mision'] == 'Desarrollar prototipos robóticos innovadores.'
    assert data['vision'] == 'Ser líderes nacionales en investigación de robótica aplicada.'


@pytest.mark.django_db
def test_unauthenticated_cannot_access(api_client):
    resp = api_client.get(URL)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_estudiante_can_list_lineas(auth_client, estudiante, linea):
    client = auth_client(estudiante)
    resp = client.get(URL)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_estudiante_cannot_create_linea(auth_client, estudiante):
    client = auth_client(estudiante)
    resp = client.post(URL, {
        'nombre': 'Intento no autorizado',
        'descripcion': 'x',
        'mision': 'x',
        'vision': 'x',
        'is_active': True,
    }, format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_director_semillero_cannot_create_linea(auth_client, director_semillero):
    client = auth_client(director_semillero)
    resp = client.post(URL, {
        'nombre': 'Intento no autorizado',
        'descripcion': 'x',
        'mision': 'x',
        'vision': 'x',
        'is_active': True,
    }, format='json')
    assert resp.status_code == 403
