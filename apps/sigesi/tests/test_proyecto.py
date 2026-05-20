"""Smoke tests for /api/v1/core/proyectos/ — RBAC scoping + aval gate."""
import pytest


URL = '/api/v1/core/proyectos/'


@pytest.mark.django_db
def test_director_grupo_can_create_proyecto_in_aprobado_semillero(
    auth_client, director_grupo, semillero_aprobado
):
    client = auth_client(director_grupo)
    resp = client.post(URL, {
        'titulo': 'Nuevo Proyecto',
        'codigo': 'PNEW',
        'descripcion': 'desc',
        'objetivo_general': 'og',
        'semilleros': [semillero_aprobado.id],
        'estado': 'idea',
    }, format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_create_proyecto_with_sin_aprobar_semillero_returns_400(
    auth_client, director_grupo, semillero_sin_aprobar
):
    """Aval gate: ALL linked semilleros must be aprobado for non-admins."""
    client = auth_client(director_grupo)
    resp = client.post(URL, {
        'titulo': 'X',
        'codigo': 'PX',
        'descripcion': 'd',
        'objetivo_general': 'o',
        'semilleros': [semillero_sin_aprobar.id],
        'estado': 'idea',
    }, format='json')
    assert resp.status_code == 400
    assert 'aval aprobado' in resp.content.decode().lower()


@pytest.mark.django_db
def test_admin_sees_all_proyectos(auth_client, admin_user, proyecto):
    client = auth_client(admin_user)
    resp = client.get(URL)
    assert resp.status_code == 200
    ids = [p['id'] for p in resp.json()['results']]
    assert proyecto.id in ids


@pytest.mark.django_db
def test_estudiante_only_sees_proyectos_they_belong_to(
    auth_client, otro_estudiante, proyecto
):
    """otro_estudiante is not linked to `proyecto`, so it should not appear."""
    client = auth_client(otro_estudiante)
    resp = client.get(URL)
    assert resp.status_code == 200
    ids = [p['id'] for p in resp.json()['results']]
    assert proyecto.id not in ids
