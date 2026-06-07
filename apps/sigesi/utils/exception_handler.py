"""Manejador de excepciones global de DRF.

Convierte en JSON limpio y en español las excepciones que DRF no atrapa por sí
solo (que de otro modo se traducirían en un HTML 500 o una respuesta vacía).
**No modifica** ninguna respuesta que DRF ya construya (validaciones de
serializer, 401/403/404), por lo que las formas de respuesta existentes se
conservan intactas. Solo cuando DRF devuelve ``None`` se mapean:

- ``IntegrityError`` → 400 con mensaje de conflicto en español.
- ``DataError`` → 400 (valor fuera del tamaño permitido).
- ``ValidationError`` de Django (modelo) → 400 con sus mensajes unidos.
- ``OperationalError`` / ``DatabaseError`` → 503 (base de datos no disponible).
- cualquier otra excepción → 500 con ``{'detail': '...'}`` (nunca HTML).

Todas las ramas registran en el log el detalle real para facilitar la
depuración sin exponerlo al cliente.
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError, DataError, IntegrityError, OperationalError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def _mensaje_integridad(exc: Exception) -> str:
    """Deriva un mensaje en español a partir de un ``IntegrityError`` de unicidad.

    Inspecciona el texto del error para nombrar el campo en conflicto (cédula,
    correo personal o email institucional). Si no logra identificarlo, devuelve
    un mensaje genérico de conflicto.

    Args:
        exc: La excepción de integridad capturada.

    Returns:
        El mensaje en español describiendo el conflicto.
    """
    texto = str(exc).lower()
    if 'cedula' in texto or 'cédula' in texto:
        return 'Ya existe un usuario registrado con esta cédula.'
    if 'correo_personal' in texto:
        return 'Ya existe un usuario registrado con este correo personal.'
    if 'email' in texto:
        return 'Ya existe un usuario registrado con este correo electrónico.'
    if 'unique' in texto or 'duplicate' in texto or 'llave duplicada' in texto:
        return 'Ya existe un registro con uno de los valores enviados.'
    return 'No se pudo completar la operación por un conflicto de datos.'


def custom_exception_handler(exc, context) -> Response:
    """Maneja excepciones no atrapadas por DRF devolviendo JSON en español.

    Primero delega en el manejador estándar de DRF; si este produce una
    respuesta, se devuelve sin cambios (se preservan los cuerpos existentes,
    incluidos 401/403/404 y los errores de validación de serializer). Solo
    cuando DRF devuelve ``None`` se mapean los errores no controlados.

    Args:
        exc: La excepción lanzada durante el procesamiento de la petición.
        context: El contexto de DRF (incluye la vista bajo ``'view'``).

    Returns:
        La ``Response`` apropiada: la de DRF si existe, o una construida aquí
        para los errores de base de datos y las excepciones no controladas.
    """
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    vista = context.get('view')

    if isinstance(exc, IntegrityError):
        logger.warning('IntegrityError en %s: %s', vista, exc)
        return Response(
            {'detail': _mensaje_integridad(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, DataError):
        logger.warning('DataError en %s: %s', vista, exc)
        return Response(
            {'detail': 'Uno de los valores enviados excede el tamaño permitido.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, DjangoValidationError):
        mensajes = exc.messages if hasattr(exc, 'messages') else [str(exc)]
        logger.warning('ValidationError de modelo en %s: %s', vista, mensajes)
        return Response(
            {'detail': ' '.join(mensajes)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # OperationalError/DatabaseError: la base de datos no está disponible o la
    # operación falló a nivel de motor. Se responde 503 (servicio no disponible)
    # para que el cliente pueda reintentar. OperationalError es subclase de
    # DatabaseError, pero se evalúa primero por claridad del log.
    if isinstance(exc, (OperationalError, DatabaseError)):
        logger.exception('Error de base de datos en %s', vista)
        return Response(
            {'detail': 'El servicio no está disponible temporalmente. Intente nuevamente más tarde.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Excepción no controlada: registrar el detalle real y responder limpio.
    logger.exception('Excepción no controlada en %s', vista)
    return Response(
        {'detail': 'Error interno del servidor. Intente nuevamente más tarde.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
