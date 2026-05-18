"""Smoke tests for the /api/v1/auth/ endpoints."""
import pytest


LOGIN_URL = '/api/v1/auth/login/'
REFRESH_URL = '/api/v1/auth/refresh/'
RECUPERACION_URL = '/api/v1/auth/recuperacion/'


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
