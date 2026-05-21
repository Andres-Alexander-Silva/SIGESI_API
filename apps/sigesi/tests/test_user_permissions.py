"""Permisos del endpoint /users/:
- Solo administrador hace CRUD completo.
- Otros roles: solo lectura.
- Otros roles: pueden actualizar su propio correo personal.
"""
import pytest

from apps.sigesi.models import User

URL = '/api/v1/config/users/'
ME_EMAIL_URL = '/api/v1/config/users/me/correo-personal/'


def _nuevo_usuario_payload(**over):
    data = {
        'username': 'nuevo1',
        'cedula': 'NU000001',
        'first_name': 'Nuevo',
        'last_name': 'Usuario',
        'email': 'nuevo1@ufps.edu.co',
        'correo_personal': 'nuevo1@gmail.com',
        'password': 'claveSegura1',
        'codigo_estudiantil': '1720001',
        'roles': ['estudiante'],
    }
    data.update(over)
    return data


# ---------------------------------------------------------------- create

@pytest.mark.django_db
def test_admin_can_create_user(auth_client, admin_user):
    client = auth_client(admin_user)
    resp = client.post(URL, _nuevo_usuario_payload(), format='json')
    assert resp.status_code == 201, resp.content
    assert User.objects.filter(correo_personal='nuevo1@gmail.com').exists()


@pytest.mark.django_db
def test_non_admin_cannot_create_user(auth_client, estudiante):
    client = auth_client(estudiante)
    resp = client.post(URL, _nuevo_usuario_payload(), format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_anonymous_cannot_create_user(api_client):
    resp = api_client.post(URL, _nuevo_usuario_payload(), format='json')
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------- read

@pytest.mark.django_db
def test_non_admin_can_list_and_retrieve(auth_client, estudiante, director_grupo):
    client = auth_client(estudiante)
    assert client.get(URL).status_code == 200
    assert client.get(f'{URL}{director_grupo.id}/').status_code == 200


# ---------------------------------------------------------------- update / delete

@pytest.mark.django_db
def test_non_admin_cannot_update_other_user(auth_client, estudiante, director_grupo):
    client = auth_client(estudiante)
    resp = client.patch(f'{URL}{director_grupo.id}/', {'first_name': 'Hack'}, format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_non_admin_cannot_delete_user(auth_client, estudiante, director_grupo):
    client = auth_client(estudiante)
    resp = client.delete(f'{URL}{director_grupo.id}/')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_admin_can_update_and_delete(auth_client, admin_user, estudiante):
    client = auth_client(admin_user)
    upd = client.patch(f'{URL}{estudiante.id}/', {'first_name': 'Editado'}, format='json')
    assert upd.status_code == 200, upd.content
    estudiante.refresh_from_db()
    assert estudiante.first_name == 'Editado'
    assert client.delete(f'{URL}{estudiante.id}/').status_code == 204


# ---------------------------------------------------------------- me/correo-personal

@pytest.mark.django_db
def test_non_admin_updates_own_personal_email(auth_client, estudiante):
    client = auth_client(estudiante)
    resp = client.patch(ME_EMAIL_URL, {'correo_personal': 'nuevo_personal@gmail.com'}, format='json')
    assert resp.status_code == 200, resp.content
    estudiante.refresh_from_db()
    assert estudiante.correo_personal == 'nuevo_personal@gmail.com'


@pytest.mark.django_db
def test_me_email_only_changes_own_account(auth_client, estudiante, director_grupo):
    """El endpoint actúa sobre el usuario autenticado; no puede tocar a otro."""
    client = auth_client(estudiante)
    correo_director = director_grupo.correo_personal
    client.patch(ME_EMAIL_URL, {'correo_personal': 'solo_mio@gmail.com'}, format='json')
    director_grupo.refresh_from_db()
    assert director_grupo.correo_personal == correo_director


@pytest.mark.django_db
def test_me_email_rejects_duplicate(auth_client, estudiante, director_grupo):
    client = auth_client(estudiante)
    resp = client.patch(
        ME_EMAIL_URL, {'correo_personal': director_grupo.correo_personal}, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_me_email_requires_authentication(api_client):
    resp = api_client.patch(ME_EMAIL_URL, {'correo_personal': 'x@gmail.com'}, format='json')
    assert resp.status_code == 401
