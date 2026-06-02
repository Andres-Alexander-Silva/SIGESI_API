"""Manejador de excepciones global de DRF.

Convierte en JSON limpio y en español las excepciones que DRF no atrapa por sí
solo (que de otro modo se traducirían en un HTML 500 o una respuesta vacía):
errores de integridad de la base de datos, valores fuera de rango y cualquier
excepción no controlada. **No modifica** ninguna respuesta que DRF ya construya
(validaciones de serializer, 401/403/404), por lo que las formas de respuesta
existentes se conservan intactas.
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DataError, IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def _mensaje_integridad(exc):
    """Deriva un mensaje en español a partir de un ``IntegrityError`` de unicidad.

    Inspecciona el texto del error para nombrar el campo en conflicto (cédula,
    correo personal o email institucional). Si no logra identificarlo, devuelve
    un mensaje genérico de conflicto.
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


def custom_exception_handler(exc, context):
    """Maneja excepciones no atrapadas por DRF devolviendo JSON en español.

    Primero delega en el manejador estándar de DRF; si este produce una
    respuesta, se devuelve sin cambios (se preservan los cuerpos existentes).
    Solo cuando DRF devuelve ``None`` se mapean los errores no controlados:

    - ``IntegrityError`` → 400 con mensaje de conflicto en español.
    - ``DataError`` → 400 (valor fuera del tamaño permitido).
    - ``ValidationError`` de Django (modelo) → 400 con sus mensajes unidos.
    - cualquier otra excepción → 500 con ``{'detail': '...'}`` (nunca HTML).
    """
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, IntegrityError):
        return Response(
            {'detail': _mensaje_integridad(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, DataError):
        return Response(
            {'detail': 'Uno de los valores enviados excede el tamaño permitido.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, DjangoValidationError):
        mensajes = exc.messages if hasattr(exc, 'messages') else [str(exc)]
        return Response(
            {'detail': ' '.join(mensajes)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Excepción no controlada: registrar el detalle real y responder limpio.
    logger.exception('Excepción no controlada en %s', context.get('view'))
    return Response(
        {'detail': 'Error interno del servidor. Intente nuevamente más tarde.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
