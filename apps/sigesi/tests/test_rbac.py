"""Tests de control de acceso para /api/v1/config/{menus,opciones,permisos}/.

Antes de este fix, los tres ViewSets usaban IsAuthenticated a secas: cualquier
usuario autenticado (incluido un estudiante) podía asignarse permisos de
administrador vía POST /permisos/. Ahora usan AdminOrReadOnlyPermission:
lectura abierta a cualquier autenticado, escritura reservada al administrador.
"""
import pytest

from apps.sigesi.models import Menu, Opcion, Permiso

MENUS_URL = '/api/v1/config/menus/'
OPCIONES_URL = '/api/v1/config/opciones/'
PERMISOS_URL = '/api/v1/config/permisos/'


@pytest.fixture
def menu(db):
    return Menu.objects.create(nombre='Configuración', icono='settings')


@pytest.fixture
def opcion(db, menu):
    return Opcion.objects.create(menu=menu, nombre='Usuarios', url='/config/usuarios')


@pytest.mark.django_db
def test_admin_can_create_menu(auth_client, admin_user):
    client = auth_client(admin_user)
    resp = client.post(MENUS_URL, {'nombre': 'Reportes', 'icono': 'bar_chart'}, format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_create_menu(auth_client, estudiante):
    client = auth_client(estudiante)
    resp = client.post(MENUS_URL, {'nombre': 'Intento', 'icono': 'x'}, format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_estudiante_can_list_menus(auth_client, estudiante, menu):
    client = auth_client(estudiante)
    resp = client.get(MENUS_URL)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_estudiante_cannot_create_opcion(auth_client, estudiante, menu):
    client = auth_client(estudiante)
    resp = client.post(OPCIONES_URL, {
        'menu': menu.id, 'nombre': 'Intento', 'url': '/x',
    }, format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_estudiante_cannot_self_grant_admin_permission(auth_client, estudiante, opcion):
    """Regresión del hallazgo crítico: un estudiante no puede otorgarse a sí
    mismo (ni a ningún rol) permisos vía /permisos/."""
    client = auth_client(estudiante)
    resp = client.post(PERMISOS_URL, {
        'rol': 'estudiante',
        'opcion': opcion.id,
        'puede_consultar': True,
        'puede_crear': True,
        'puede_actualizar': True,
        'puede_eliminar': True,
    }, format='json')
    assert resp.status_code == 403
    assert not Permiso.objects.filter(opcion=opcion, rol='estudiante').exists()


@pytest.mark.django_db
def test_admin_can_create_permiso(auth_client, admin_user, opcion):
    client = auth_client(admin_user)
    resp = client.post(PERMISOS_URL, {
        'rol': 'estudiante',
        'opcion': opcion.id,
        'puede_consultar': True,
        'puede_crear': False,
        'puede_actualizar': False,
        'puede_eliminar': False,
    }, format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_unauthenticated_cannot_access_permisos(api_client):
    resp = api_client.get(PERMISOS_URL)
    assert resp.status_code == 401
