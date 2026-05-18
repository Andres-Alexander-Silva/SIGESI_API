"""Smoke tests for /api/v1/core/programas-academicos/ — admin writes, others read."""
import pytest


URL = '/api/v1/core/programas-academicos/'


@pytest.mark.django_db
def test_admin_can_create_programa(auth_client, admin_user):
    client = auth_client(admin_user)
    resp = client.post(URL, {
        'nombre': 'Medicina',
        'codigo': 'MED',
        'facultad': 'Ciencias de la Salud',
    }, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.json()['codigo'] == 'MED'


@pytest.mark.django_db
def test_director_grupo_cannot_create_programa(auth_client, director_grupo):
    client = auth_client(director_grupo)
    resp = client.post(URL, {'nombre': 'X', 'codigo': 'X', 'facultad': 'X'}, format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_any_authenticated_user_can_list_programas(auth_client, estudiante, programa):
    client = auth_client(estudiante)
    resp = client.get(URL)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_unauthenticated_returns_401(api_client):
    resp = api_client.get(URL)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_admin_can_delete_programa(auth_client, admin_user, programa):
    client = auth_client(admin_user)
    resp = client.delete(f'{URL}{programa.id}/')
    assert resp.status_code == 204
