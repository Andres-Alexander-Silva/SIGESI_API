"""Smoke tests for the /api/v1/auth/ endpoints + el flujo de token exchange."""
import types

import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

from apps.sigesi.decorators.permissions import HasRolePermission, active_role
from apps.sigesi.utils.tokens import IdentityToken, build_context_tokens

User = get_user_model()

LOGIN_URL = '/api/v1/auth/login/'
SELECT_ROLE_URL = '/api/v1/auth/select-role/'
REFRESH_URL = '/api/v1/auth/refresh/'
RECUPERACION_URL = '/api/v1/auth/recuperacion/'


def _multi_role_user(roles=('director_semillero', 'estudiante')):
    user = User.objects.create(
        username=f"mr_{User.objects.count() + 1}",
        cedula=f"MR{User.objects.count() + 1:06d}",
        correo_personal=f"mr{User.objects.count() + 1}@example.com",
        email=f"mr{User.objects.count() + 1}@ufps.edu.co",
        roles=list(roles),
        is_active=True,
    )
    user.set_password('x')
    user.save()
    return user


@pytest.mark.django_db
def test_login_with_valid_credentials_returns_tokens(api_client, estudiante):
    resp = api_client.post(LOGIN_URL, {'email': estudiante.email, 'password': 'x'}, format='json')
    assert resp.status_code == 200
    body = resp.json()
    assert body['token']
    assert body['refreshToken']
    assert body['usuarioId'] == estudiante.id
    assert body['email'] == estudiante.email


@pytest.mark.django_db
def test_login_single_role_auto_selects(api_client, estudiante):
    """Rol único → login devuelve tokens de contexto con el claim `role`."""
    resp = api_client.post(LOGIN_URL, {'email': estudiante.email, 'password': 'x'}, format='json')
    assert resp.status_code == 200
    body = resp.json()
    assert body['response'] == 'OK'
    assert body['role'] == 'estudiante'
    assert AccessToken(body['token'])['role'] == 'estudiante'


@pytest.mark.django_db
def test_login_multi_role_returns_identity_token(api_client):
    user = _multi_role_user()
    resp = api_client.post(LOGIN_URL, {'email': user.email, 'password': 'x'}, format='json')
    assert resp.status_code == 200
    body = resp.json()
    assert body['response'] == 'SELECT_ROLE'
    assert body['identityToken']
    assert 'token' not in body
    codes = {r['code'] for r in body['available_roles']}
    assert codes == {'director_semillero', 'estudiante'}


@pytest.mark.django_db
def test_select_role_with_identity_token_embeds_claims(api_client):
    user = _multi_role_user()
    login = api_client.post(LOGIN_URL, {'email': user.email, 'password': 'x'}, format='json')
    identity = login.json()['identityToken']

    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {identity}')
    resp = api_client.post(SELECT_ROLE_URL, {'role': 'director_semillero'}, format='json')
    assert resp.status_code == 200
    access = AccessToken(resp.json()['token'])
    assert access['role'] == 'director_semillero'
    assert {r['code'] for r in access['available_roles']} == {'director_semillero', 'estudiante'}


@pytest.mark.django_db
def test_select_role_hot_switch_with_access_token(api_client):
    """Cambio de rol en caliente: un Access JWT vigente sirve para re-seleccionar."""
    user = _multi_role_user()
    _, access = build_context_tokens(user, 'estudiante')

    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    resp = api_client.post(SELECT_ROLE_URL, {'role': 'director_semillero'}, format='json')
    assert resp.status_code == 200
    assert AccessToken(resp.json()['token'])['role'] == 'director_semillero'


@pytest.mark.django_db
def test_select_role_unowned_role_returns_403(api_client):
    user = _multi_role_user(roles=('estudiante',))
    identity = str(IdentityToken.for_user(user))
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {identity}')
    resp = api_client.post(SELECT_ROLE_URL, {'role': 'administrador'}, format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_refresh_keeps_role_claim(api_client, estudiante):
    login = api_client.post(LOGIN_URL, {'email': estudiante.email, 'password': 'x'}, format='json')
    refresh_token = login.json()['refreshToken']
    resp = api_client.post(REFRESH_URL, {'refreshToken': refresh_token}, format='json')
    assert resp.status_code == 200
    assert AccessToken(resp.json()['token'])['role'] == 'estudiante'


# --------------------------------------------------------------- HasRolePermission

@pytest.mark.django_db
def test_has_role_permission_rejects_identity_token():
    user = _multi_role_user()
    request = types.SimpleNamespace(auth=IdentityToken.for_user(user), user=user)
    view = types.SimpleNamespace(required_roles=None)
    assert HasRolePermission().has_permission(request, view) is False


@pytest.mark.django_db
def test_has_role_permission_allows_context_token_without_required_roles():
    user = _multi_role_user()
    _, access = build_context_tokens(user, 'estudiante')
    request = types.SimpleNamespace(auth=access, user=user)
    view = types.SimpleNamespace(required_roles=None)
    assert HasRolePermission().has_permission(request, view) is True
    assert active_role(request) == 'estudiante'


@pytest.mark.django_db
def test_has_role_permission_enforces_required_roles():
    user = _multi_role_user()
    _, access = build_context_tokens(user, 'estudiante')
    request = types.SimpleNamespace(auth=access, user=user)

    assert HasRolePermission().has_permission(
        request, types.SimpleNamespace(required_roles=['administrador'])) is False
    assert HasRolePermission().has_permission(
        request, types.SimpleNamespace(required_roles=['estudiante'])) is True


@pytest.mark.django_db
def test_login_with_wrong_password_returns_400(api_client, estudiante):
    resp = api_client.post(LOGIN_URL, {'email': estudiante.email, 'password': 'wrong'}, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_login_inactive_user_returns_403(api_client, estudiante):
    estudiante.is_active = False
    estudiante.save()
    resp = api_client.post(LOGIN_URL, {'email': estudiante.email, 'password': 'x'}, format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_refresh_with_valid_token_returns_new_access(api_client, estudiante):
    login = api_client.post(LOGIN_URL, {'email': estudiante.email, 'password': 'x'}, format='json')
    refresh_token = login.json()['refreshToken']

    resp = api_client.post(REFRESH_URL, {'refreshToken': refresh_token}, format='json')
    assert resp.status_code == 200
    body = resp.json()
    assert body['token']
    assert body['refreshToken']


@pytest.mark.django_db
def test_refresh_with_invalid_token_returns_401(api_client):
    resp = api_client.post(REFRESH_URL, {'refreshToken': 'not-a-jwt'}, format='json')
    assert resp.status_code == 401


@pytest.mark.django_db
def test_recuperacion_with_unknown_email_returns_generic_message(api_client):
    """Anti-enumeration: unknown emails still return 200 with the same message."""
    resp = api_client.post(RECUPERACION_URL, {'email': 'nobody@example.com'}, format='json')
    assert resp.status_code == 200
    assert 'recibirás un enlace' in resp.json()['message']
