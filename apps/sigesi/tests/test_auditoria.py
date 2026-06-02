"""Tests de auditoría y registro operacional del sistema.

A diferencia del resto de la suite, estos tests autentican con **JWT real**
(``build_context_tokens`` + ``credentials``) en lugar del fixture
``auth_client`` (``force_authenticate``), porque el ``AuditoriaMiddleware``
identifica al usuario y su rol activo decodificando el ``Bearer`` de la
petición; ``force_authenticate`` no envía token y no ejercitaría el middleware.
"""
import pytest

from apps.sigesi.models import RegistroAuditoria
from apps.sigesi.utils.tokens import build_context_tokens

pytestmark = pytest.mark.django_db

LOGIN_URL = '/api/v1/auth/login/'
LOGS_URL = '/api/v1/config/auditoria/logs/'
ACTIVIDADES_URL = '/api/v1/core/actividades/'


def _auth(api_client, user, role):
    """Autentica el cliente con un access token de contexto real del rol dado."""
    _, access = build_context_tokens(user, role)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    return api_client


def _filas(api_client):
    """Extrae la lista de registros de la respuesta paginada ``{success, data}``."""
    resp = api_client.get(LOGS_URL)
    body = resp.json()
    data = body['data']
    return body, data['results'] if isinstance(data, dict) else data


# ---------------------------------------------------------------------------
# El middleware registra las escrituras exitosas
# ---------------------------------------------------------------------------

def test_eliminacion_genera_registro(api_client, admin_user, actividad):
    """Un DELETE exitoso crea una fila con accion/modulo/usuario/rol correctos."""
    _auth(api_client, admin_user, 'administrador')

    resp = api_client.delete(f'{ACTIVIDADES_URL}{actividad.id}/')
    assert resp.status_code == 204

    registro = RegistroAuditoria.objects.get(accion='eliminacion')
    assert registro.modulo == 'actividades'
    assert registro.usuario_email == admin_user.email
    assert registro.rol_activo == 'administrador'
    assert registro.object_id == str(actividad.id)
    assert registro.metodo_http == 'DELETE'


def test_creacion_genera_registro(api_client, admin_user, proyecto):
    """Un POST exitoso queda auditado como accion='creacion'."""
    _auth(api_client, admin_user, 'administrador')

    payload = {
        'proyecto': proyecto.id,
        'titulo': 'Nueva actividad',
        'descripcion': 'desc',
        'responsable': proyecto.lider_id,
        'fecha_inicio': '2026-06-01',
        'fecha_fin': '2026-06-02',
    }
    resp = api_client.post(ACTIVIDADES_URL, payload, format='json')
    assert resp.status_code == 201

    registro = RegistroAuditoria.objects.get(accion='creacion')
    assert registro.modulo == 'actividades'
    assert registro.usuario_email == admin_user.email


# ---------------------------------------------------------------------------
# El middleware NO registra lecturas ni intentos fallidos
# ---------------------------------------------------------------------------

def test_lectura_get_no_genera_registro(api_client, admin_user, actividad):
    """Las lecturas GET no se auditan (evita inundar la tabla)."""
    _auth(api_client, admin_user, 'administrador')

    resp = api_client.get(ACTIVIDADES_URL)
    assert resp.status_code == 200
    assert RegistroAuditoria.objects.count() == 0


def test_escritura_denegada_no_genera_registro(api_client, estudiante, proyecto):
    """Un POST que termina en 403 no se audita (solo se registran < 400)."""
    _auth(api_client, estudiante, 'estudiante')

    payload = {
        'proyecto': proyecto.id,
        'titulo': 'No permitida',
        'descripcion': 'desc',
        'responsable': estudiante.id,
        'fecha_inicio': '2026-06-01',
        'fecha_fin': '2026-06-02',
    }
    resp = api_client.post(ACTIVIDADES_URL, payload, format='json')
    assert resp.status_code == 403
    assert RegistroAuditoria.objects.count() == 0


# ---------------------------------------------------------------------------
# Eventos de autenticación
# ---------------------------------------------------------------------------

def test_login_genera_registro_autenticacion(api_client, estudiante):
    """Un login exitoso (rol único) queda auditado como accion='autenticacion'."""
    resp = api_client.post(
        LOGIN_URL, {'email': estudiante.email, 'password': 'x'}, format='json')
    assert resp.status_code == 200

    registro = RegistroAuditoria.objects.get(accion='autenticacion')
    assert registro.modulo == 'autenticacion'
    assert registro.usuario_email == estudiante.email


# ---------------------------------------------------------------------------
# Endpoint de consulta: solo administrador
# ---------------------------------------------------------------------------

def test_logs_admin_obtiene_sobre_success(api_client, admin_user, actividad):
    """El admin lista la traza con el sobre {success, data}."""
    _auth(api_client, admin_user, 'administrador')
    api_client.delete(f'{ACTIVIDADES_URL}{actividad.id}/')

    body, filas = _filas(api_client)
    assert body['success'] is True
    assert any(
        f['accion'] == 'eliminacion'
        and f['modulo'] == 'actividades'
        and f['usuario'] == admin_user.email
        for f in filas
    )


@pytest.mark.parametrize('role', [
    'estudiante', 'director_grupo', 'director_semillero', 'lider_estudiantil',
])
def test_logs_no_admin_403(api_client, request, role):
    """Cualquier rol distinto de administrador recibe 403 en la auditoría."""
    user = request.getfixturevalue(role)
    _auth(api_client, user, role)

    resp = api_client.get(LOGS_URL)
    assert resp.status_code == 403


def test_logs_endpoint_no_se_autoaudita(api_client, admin_user):
    """Consultar la auditoría no genera registros (ruta excluida)."""
    _auth(api_client, admin_user, 'administrador')

    api_client.get(LOGS_URL)
    assert RegistroAuditoria.objects.count() == 0
