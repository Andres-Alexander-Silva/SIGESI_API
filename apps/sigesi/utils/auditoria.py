"""Lógica compartida para la auditoría y trazabilidad institucional.

Punto único reutilizado por :class:`apps.sigesi.middleware.audit_middleware.AuditoriaMiddleware`.
Mantiene el middleware delgado: aquí viven la decodificación del token JWT, la
resolución de (módulo, object_id) a partir de la ruta y la escritura tolerante
a fallos del :class:`apps.sigesi.models.RegistroAuditoria`.

Todas las funciones son defensivas: un error de auditoría **nunca** debe
propagarse al cliente; se registra con ``logging`` y se ignora.
"""
import logging

from rest_framework_simplejwt.tokens import AccessToken

from apps.sigesi.models import RegistroAuditoria, User

logger = logging.getLogger(__name__)

# Método HTTP de escritura → acción auditada.
METODO_A_ACCION = {
    'POST': RegistroAuditoria.AccionChoices.CREACION,
    'PUT': RegistroAuditoria.AccionChoices.ACTUALIZACION,
    'PATCH': RegistroAuditoria.AccionChoices.ACTUALIZACION,
    'DELETE': RegistroAuditoria.AccionChoices.ELIMINACION,
}

# Rutas que no se auditan (ruido / autorreferencia del propio endpoint).
RUTAS_EXCLUIDAS = (
    '/swagger/',
    '/redoc/',
    '/api/v1/ping/',
    '/api/v1/health/',
    '/api/v1/config/auditoria/',
)

# Rutas de autenticación: generan eventos accion='autenticacion'.
RUTAS_AUTENTICACION = (
    '/api/v1/auth/login/',
    '/api/v1/auth/select-role/',
    '/api/v1/auth/refresh/',
)


def ruta_excluida(path):
    """Indica si la ruta debe omitirse de la auditoría."""
    return any(path.startswith(p) for p in RUTAS_EXCLUIDAS)


def es_ruta_autenticacion(path):
    """Indica si la ruta corresponde a un evento de autenticación."""
    return any(path.startswith(p) for p in RUTAS_AUTENTICACION)


def resolver_modulo(path):
    """Resuelve ``(modulo, object_id)`` a partir de la ruta de la petición.

    Parsea ``/api/v1/<capa>/<modulo>/<id?>/...`` y devuelve el slug del recurso
    y, si el siguiente segmento es numérico, su id (como cadena). Para rutas de
    autenticación devuelve ``('autenticacion', '')``.

    Devuelve ``('', '')`` cuando no logra inferir el módulo.
    """
    if es_ruta_autenticacion(path):
        return 'autenticacion', ''
    # Segmentos no vacíos: ['api', 'v1', '<capa>', '<modulo>', '<id?>', ...]
    segmentos = [s for s in path.split('/') if s]
    if len(segmentos) >= 4 and segmentos[0] == 'api':
        modulo = segmentos[3]
        object_id = ''
        if len(segmentos) >= 5 and segmentos[4].isdigit():
            object_id = segmentos[4]
        return modulo, object_id
    return '', ''


def _claims_de_token(token):
    """Valida un access token y devuelve ``{user_id, role, token_use}`` o ``None``."""
    if not token:
        return None
    try:
        validado = AccessToken(token)
    except Exception:  # noqa: BLE001 — token inválido/expirado: no audita por token
        return None
    return {
        'user_id': validado.get('user_id'),
        'role': validado.get('role') or '',
        'token_use': validado.get('token_use'),
    }


def claims_desde_header(request):
    """Decodifica el ``Bearer`` del header ``Authorization`` de la petición."""
    auth_header = request.META.get('HTTP_AUTHORIZATION') or ''
    if not auth_header:
        return None
    partes = auth_header.split(' ', 1)
    token = partes[1] if len(partes) == 2 else partes[0]
    return _claims_de_token(token)


def claims_desde_respuesta(response):
    """Decodifica el access token que devuelve un endpoint de autenticación.

    En ``login`` no hay ``Bearer`` entrante: el usuario se identifica a partir
    del token de contexto emitido en la respuesta. Las vistas de auth exponen el
    access bajo la clave ``token`` (login/select-role) o ``accessToken``
    (refresh); para multi-rol solo está ``identityToken``.
    """
    data = getattr(response, 'data', None)
    if not isinstance(data, dict):
        return None
    token = (data.get('token') or data.get('accessToken')
             or data.get('access') or data.get('identityToken'))
    return _claims_de_token(token)


def _email_de_usuario(user_id):
    """Correo institucional (o personal) del usuario, para el snapshot histórico."""
    if not user_id:
        return ''
    user = User.objects.filter(pk=user_id).only(
        'email', 'correo_personal').first()
    if not user:
        return ''
    return user.email or user.correo_personal or ''


def registrar(*, claims, accion, modulo, metodo, ruta, status_code,
              ip=None, user_agent='', object_id=''):
    """Crea una fila :class:`RegistroAuditoria`. Tolerante a fallos.

    ``claims`` es el dict devuelto por :func:`claims_desde_header` /
    :func:`claims_desde_respuesta` (``{user_id, role, ...}``) o ``None``. Un
    fallo al persistir se registra y se ignora para no afectar la respuesta.
    """
    try:
        user_id = (claims or {}).get('user_id')
        rol = (claims or {}).get('role', '') or ''
        RegistroAuditoria.objects.create(
            usuario_id=user_id,
            usuario_email=_email_de_usuario(user_id),
            rol_activo=rol,
            accion=accion,
            modulo=modulo,
            metodo_http=metodo,
            ruta=ruta[:255],
            status_code=status_code,
            object_id=object_id,
            ip=ip,
            user_agent=user_agent,
        )
    except Exception:  # noqa: BLE001 — la auditoría nunca rompe la petición
        logger.exception('No se pudo registrar la auditoría para %s %s', metodo, ruta)
