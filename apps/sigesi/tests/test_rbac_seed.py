"""Tests del RBAC del modulo documental (HU-021). Ver seed_rbac.py.

Cubre la regresion de H1: el cliente invoca can(url, accion) para
/avances, /produccion, /participaciones_evento, /eventos, /proyectos y
/actividades, pero antes de esta fase ninguna de esas URLs tenia una fila
Opcion — can() falla en cerrado (ver PermissionsContext.tsx en
SIGESI_CLIENT) y ningun rol, ni el administrador, podia escribir en esas
paginas.
"""
import pytest
from django.core.management import call_command

from apps.sigesi.models import Menu, Opcion, Permiso, User

# URLs del modulo documental de HU-021 (no la totalidad de rutas del cliente:
# seed_rbac.py cubre deliberadamente solo estas seis).
DOCUMENTAL_URLS = [
    '/avances',
    '/produccion',
    '/participaciones_evento',
    '/eventos',
    '/proyectos',
    '/actividades',
]


@pytest.mark.django_db
def test_seed_rbac_creates_documental_options():
    call_command('seed_rbac')
    for url in DOCUMENTAL_URLS:
        assert Opcion.objects.filter(url=url).exists(), f'falta Opcion para {url}'


@pytest.mark.django_db
def test_seed_rbac_is_idempotent():
    call_command('seed_rbac')
    menus_1 = Menu.objects.count()
    opciones_1 = Opcion.objects.count()
    permisos_1 = Permiso.objects.count()

    call_command('seed_rbac')

    assert Menu.objects.count() == menus_1
    assert Opcion.objects.count() == opciones_1
    assert Permiso.objects.count() == permisos_1


@pytest.mark.django_db
@pytest.mark.parametrize('url', DOCUMENTAL_URLS)
def test_documental_option_exists_for_client_url(url):
    call_command('seed_rbac')
    assert Opcion.objects.filter(url=url).exists()


@pytest.mark.django_db
def test_menu_documental_no_duplica_icono_existente():
    """Menu.icono es unique=True; los seis menus base usan fa-gauge,
    fa-flask, fa-users, fa-bullhorn, fa-chart-bar y fa-gear."""
    call_command('seed_rbac')
    iconos = list(Menu.objects.values_list('icono', flat=True))
    assert len(iconos) == len(set(iconos))


@pytest.mark.django_db
def test_seed_rbac_elimina_permisos_de_rol_invalido():
    """Regresion: la migracion 0003 sembro permisos para el rol 'comite',
    que nunca existio en User.RolChoices."""
    opcion = Opcion.objects.filter(url='/dashboard').first()
    if opcion is None:
        opcion = Opcion.objects.create(
            menu=Menu.objects.create(nombre='Dashboard', icono='fa-gauge'),
            nombre='Dashboard', url='/dashboard',
        )
    Permiso.objects.create(opcion=opcion, rol='comite', puede_consultar=True)

    call_command('seed_rbac')

    assert not Permiso.objects.filter(rol='comite').exists()


@pytest.mark.django_db
def test_todos_los_roles_de_permiso_son_validos():
    call_command('seed_rbac')
    roles_validos = set(User.RolChoices.values)
    roles_en_bd = set(Permiso.objects.values_list('rol', flat=True))
    assert roles_en_bd <= roles_validos


@pytest.mark.django_db
def test_mis_permisos_incluye_opciones_documentales_para_administrador(
    auth_client, admin_user,
):
    call_command('seed_rbac')
    client = auth_client(admin_user)
    resp = client.get('/api/v1/config/users/mis-permisos/')
    assert resp.status_code == 200

    urls_en_respuesta = {
        opcion['url']
        for menu in resp.json().get('menus', [])
        for opcion in menu.get('opciones', [])
    }
    for url in DOCUMENTAL_URLS:
        assert url in urls_en_respuesta, f'falta {url} en mis-permisos'
