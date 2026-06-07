"""Mensajes de error específicos en el CRUD de usuarios.

Cubre las dos clases de mejora:
- Validaciones de serializer con mensajes en español bajo la clave del campo
  correcto (campos obligatorios, únicos duplicados, formato inválido), sin
  alterar la forma del cuerpo de respuesta (``{"campo": ["mensaje"]}``).
- El manejador de excepciones global, que convierte errores no controlados
  (``IntegrityError``, excepción inesperada) en JSON limpio en español.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError, DataError, IntegrityError, OperationalError

from apps.sigesi.utils.exception_handler import custom_exception_handler

User = get_user_model()

USERS_URL = '/api/v1/config/users/'


def _payload(**overrides):
    """Payload base válido para crear un usuario por el CRUD."""
    data = {
        'username': 'nuevo_user',
        'cedula': 'CC900001',
        'correo_personal': 'nuevo_user@example.com',
        'password': 'password123',
        'first_name': 'Nuevo',
        'last_name': 'Usuario',
        'codigo_estudiantil': '900001',
        'roles': ['estudiante'],
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Campos obligatorios → mensaje en español bajo la clave del campo
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize('campo, mensaje', [
    ('cedula', 'La cédula es obligatoria.'),
    ('correo_personal', 'El correo personal es obligatorio.'),
    ('password', 'La contraseña es obligatoria.'),
    ('codigo_estudiantil', 'El código estudiantil es obligatorio.'),
    ('username', 'El nombre de usuario es obligatorio.'),
])
def test_create_campo_obligatorio(auth_client, admin_user, campo, mensaje):
    payload = _payload()
    payload.pop(campo)
    resp = auth_client(admin_user).post(USERS_URL, payload, format='json')
    assert resp.status_code == 400, resp.content[:300]
    assert resp.json()[campo][0] == mensaje


@pytest.mark.django_db
def test_create_roles_vacio(auth_client, admin_user):
    resp = auth_client(admin_user).post(
        USERS_URL, _payload(roles=[]), format='json',
    )
    assert resp.status_code == 400
    assert resp.json()['roles'][0] == 'Debe asignar al menos un rol al usuario.'


@pytest.mark.django_db
def test_create_rol_invalido(auth_client, admin_user):
    resp = auth_client(admin_user).post(
        USERS_URL, _payload(roles=['rector']), format='json',
    )
    assert resp.status_code == 400
    assert 'roles' in resp.json()


# ---------------------------------------------------------------------------
# Únicos duplicados → 400 con mensaje en español (forma de cuerpo intacta)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_cedula_duplicada(auth_client, admin_user):
    User.objects.create(
        username='ya_existe', cedula='CC900001',
        correo_personal='existe@example.com', email='existe@ufps.edu.co',
        roles=['estudiante'],
    )
    resp = auth_client(admin_user).post(USERS_URL, _payload(), format='json')
    assert resp.status_code == 400
    assert resp.json()['cedula'][0] == 'Ya existe un usuario registrado con esta cédula.'


@pytest.mark.django_db
def test_create_correo_personal_duplicado(auth_client, admin_user):
    User.objects.create(
        username='ya_existe', cedula='CC111111',
        correo_personal='nuevo_user@example.com', email='existe@ufps.edu.co',
        roles=['estudiante'],
    )
    resp = auth_client(admin_user).post(USERS_URL, _payload(), format='json')
    assert resp.status_code == 400
    assert resp.json()['correo_personal'][0] == 'Ya existe un usuario registrado con este correo personal.'


@pytest.mark.django_db
def test_create_email_institucional_duplicado(auth_client, admin_user):
    User.objects.create(
        username='ya_existe', cedula='CC111111',
        correo_personal='existe@example.com', email='ocupado@ufps.edu.co',
        roles=['estudiante'],
    )
    resp = auth_client(admin_user).post(
        USERS_URL, _payload(email='ocupado@ufps.edu.co'), format='json',
    )
    assert resp.status_code == 400
    assert resp.json()['email'][0] == 'Ya existe un usuario registrado con este correo electrónico.'


# ---------------------------------------------------------------------------
# Formato inválido
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_email_dominio_invalido(auth_client, admin_user):
    resp = auth_client(admin_user).post(
        USERS_URL, _payload(email='persona@gmail.com'), format='json',
    )
    assert resp.status_code == 400
    assert resp.json()['email'][0] == 'El correo debe pertenecer al dominio @ufps.edu.co.'


@pytest.mark.django_db
def test_create_password_corta(auth_client, admin_user):
    resp = auth_client(admin_user).post(
        USERS_URL, _payload(password='123'), format='json',
    )
    assert resp.status_code == 400
    assert resp.json()['password'][0] == 'La contraseña debe tener al menos 8 caracteres.'


# ---------------------------------------------------------------------------
# PATCH: regresión de forma para validate_email ({"email": ["..."]})
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_patch_email_duplicado_forma_estandar(auth_client, admin_user, estudiante):
    User.objects.create(
        username='dueno_email', cedula='CC222222',
        correo_personal='dueno@example.com', email='ocupado@ufps.edu.co',
        roles=['estudiante'],
    )
    resp = auth_client(admin_user).patch(
        f'{USERS_URL}{estudiante.id}/',
        {'email': 'ocupado@ufps.edu.co'},
        format='json',
    )
    assert resp.status_code == 400
    cuerpo = resp.json()
    # Forma estándar de DRF: lista de cadenas, no un dict anidado {"message": ...}.
    assert isinstance(cuerpo['email'], list)
    assert cuerpo['email'][0] == 'Ya existe un usuario registrado con este correo electrónico.'


# ---------------------------------------------------------------------------
# Manejador de excepciones global
# ---------------------------------------------------------------------------

def test_handler_integrity_error_cedula():
    resp = custom_exception_handler(
        IntegrityError('duplicate key value violates unique constraint "..._cedula_key"'),
        {'view': None},
    )
    assert resp.status_code == 400
    assert resp.data == {'detail': 'Ya existe un usuario registrado con esta cédula.'}


def test_handler_integrity_error_generico():
    resp = custom_exception_handler(IntegrityError('algo salió mal'), {'view': None})
    assert resp.status_code == 400
    assert resp.data == {'detail': 'No se pudo completar la operación por un conflicto de datos.'}


def test_handler_data_error():
    resp = custom_exception_handler(DataError('value too long'), {'view': None})
    assert resp.status_code == 400
    assert resp.data == {'detail': 'Uno de los valores enviados excede el tamaño permitido.'}


def test_handler_validation_error_de_modelo():
    resp = custom_exception_handler(
        DjangoValidationError(['Valor no permitido.', 'Revise el dato.']),
        {'view': None},
    )
    assert resp.status_code == 400
    assert resp.data == {'detail': 'Valor no permitido. Revise el dato.'}


def test_handler_operational_error_503():
    resp = custom_exception_handler(
        OperationalError('could not connect to server'), {'view': None},
    )
    assert resp.status_code == 503
    assert resp.data == {
        'detail': 'El servicio no está disponible temporalmente. Intente nuevamente más tarde.'
    }


def test_handler_database_error_503():
    resp = custom_exception_handler(DatabaseError('db caída'), {'view': None})
    assert resp.status_code == 503
    assert resp.data == {
        'detail': 'El servicio no está disponible temporalmente. Intente nuevamente más tarde.'
    }


def test_handler_excepcion_no_controlada():
    resp = custom_exception_handler(RuntimeError('explota'), {'view': None})
    assert resp.status_code == 500
    assert resp.data == {'detail': 'Error interno del servidor. Intente nuevamente más tarde.'}


@pytest.mark.django_db
def test_error_no_controlado_devuelve_json_limpio_500(auth_client, admin_user, monkeypatch):
    """Una excepción inesperada en la vista responde 500 con JSON, no HTML."""
    def boom(self, *args, **kwargs):
        raise RuntimeError('explota en save')

    monkeypatch.setattr(User, 'save', boom)
    resp = auth_client(admin_user).post(USERS_URL, _payload(), format='json')
    assert resp.status_code == 500
    assert resp.json() == {'detail': 'Error interno del servidor. Intente nuevamente más tarde.'}
