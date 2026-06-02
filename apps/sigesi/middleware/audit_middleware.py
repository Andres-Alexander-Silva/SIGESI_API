"""Middleware de auditoría y registro operacional del sistema.

Intercepta cada petición HTTP y, en la fase de respuesta, persiste la traza
institucional de las operaciones de escritura exitosas y de los eventos de
autenticación de usuarios autenticados.

A diferencia de :class:`apps.sigesi.middleware.authentication_middleware.JWTAuthentication`
(que es la clase de autenticación de DRF, no un middleware de Django), este sí
es un middleware de Django registrado en ``settings.MIDDLEWARE``. Como DRF no
escribe el usuario autenticado de vuelta en el ``HttpRequest``, este middleware
identifica al usuario y su **rol activo** decodificando el ``Bearer`` JWT por su
cuenta (o, para ``login``, el token emitido en la respuesta).

Política de registro (acordada):
  - Escrituras (``POST/PUT/PATCH/DELETE``) con ``status_code < 400``.
  - Eventos de autenticación (``login``/``select-role``/``refresh``) con 200.
  - **No** se registran lecturas ``GET`` ni los intentos fallidos (>= 400).

Toda la lógica vive en :mod:`apps.sigesi.utils.auditoria`; el middleware solo
orquesta y nunca lanza excepciones hacia el cliente.
"""
import logging

from apps.sigesi.models import RegistroAuditoria
from apps.sigesi.utils import auditoria

logger = logging.getLogger(__name__)

METODOS_ESCRITURA = frozenset({'POST', 'PUT', 'PATCH', 'DELETE'})


class AuditoriaMiddleware:
    """Registra la trazabilidad histórica de la actividad institucional."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._auditar(request, response)
        except Exception:  # noqa: BLE001 — la auditoría nunca rompe la respuesta
            logger.exception('Fallo inesperado en AuditoriaMiddleware')
        return response

    def _auditar(self, request, response):
        """Evalúa la petición/respuesta y persiste el registro si procede."""
        path = request.path
        if auditoria.ruta_excluida(path):
            return

        metodo = request.method
        status_code = getattr(response, 'status_code', 0)

        # Eventos de autenticación (login / select-role / refresh) exitosos.
        if auditoria.es_ruta_autenticacion(path):
            if status_code == 200:
                claims = (auditoria.claims_desde_header(request)
                          or auditoria.claims_desde_respuesta(response))
                auditoria.registrar(
                    claims=claims,
                    accion=RegistroAuditoria.AccionChoices.AUTENTICACION,
                    modulo='autenticacion',
                    metodo=metodo,
                    ruta=path,
                    status_code=status_code,
                    ip=self._ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                )
            return

        # Escrituras exitosas de usuarios autenticados.
        if metodo in METODOS_ESCRITURA and status_code < 400:
            claims = auditoria.claims_desde_header(request)
            if not claims or not claims.get('user_id'):
                return  # sin usuario autenticado: no se audita
            modulo, object_id = auditoria.resolver_modulo(path)
            auditoria.registrar(
                claims=claims,
                accion=auditoria.METODO_A_ACCION[metodo],
                modulo=modulo,
                metodo=metodo,
                ruta=path,
                status_code=status_code,
                ip=self._ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                object_id=object_id,
            )

    @staticmethod
    def _ip(request):
        """IP de origen: primer valor de ``X-Forwarded-For`` o ``REMOTE_ADDR``."""
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
