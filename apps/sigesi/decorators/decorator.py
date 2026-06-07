"""MÓDULO OBSOLETO — no usar.

Estos decoradores buscan ``Permiso`` por campos que ya no existen en el esquema
(``opcion__codigo``, ``opcion__is_active``, ``permitido``); los campos reales son
``opcion__url``, ``opcion__estado`` y los cuatro booleanos ``puede_*``. Ninguna
vista del proyecto los usa: el control de acceso real vive en
``apps/sigesi/decorators/permissions.py`` (clases ``*RolePermission`` +
``HasRolePermission``). Se conserva solo para no romper imports históricos;
no agregar nuevos usos y eliminarlo cuando se confirme que nada lo importa.
"""
import logging
from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from apps.sigesi.models import Permiso

logger = logging.getLogger(__name__)


def access_permission(codigo_opcion):
    """
    Decorador para verificar si un usuario tiene permisos sobre una opción específica.
    Uso: @access_permission('semilleros_ver')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            if __check_permission(request, codigo_opcion):
                return func(self, request, *args, **kwargs)
            else:
                return Response(
                    {"error": "No cuentas con permisos para ingresar a esta URL"},
                    status=status.HTTP_403_FORBIDDEN
                )
        return wrapper
    return decorator


def access_function(codigo_opcion):
    """
    Decorador para verificar si un usuario tiene privilegios para ejecutar una función.
    Uso: @access_function('proyectos_aprobar')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            if __check_privilege_func(request, codigo_opcion):
                return func(self, request, *args, **kwargs)
            else:
                return Response(
                    {"error": "No cuentas con permisos para realizar esta función"},
                    status=status.HTTP_403_FORBIDDEN
                )
        return wrapper
    return decorator


def __check_permission(request, codigo_opcion):
    """
    Verifica si el usuario tiene permiso sobre una opción por su código.
    """
    user = request.user
    logger.debug("Verificando permisos para usuario: %s", user)

    if not user.is_authenticated or not user.is_active:
        return False

    try:
        return Permiso.objects.filter(
            rol__in=user.roles,
            opcion__codigo=codigo_opcion,
            opcion__is_active=True,
            permitido=True
        ).exists()
    except Exception as e:
        logger.error("Error verificando permiso: %s", str(e))
        return False


def __check_privilege_func(request, codigo_opcion):
    """
    Verifica si el usuario tiene el permiso específico para ejecutar una acción.
    """
    user = request.user
    logger.debug("Verificando privilegios para usuario: %s", user)

    if not user.is_authenticated or not user.is_active:
        return False

    try:
        return Permiso.objects.filter(
            rol__in=user.roles,
            opcion__codigo=codigo_opcion,
            opcion__is_active=True,
            permitido=True
        ).exists()
    except Exception as e:
        logger.error("Error verificando privilegio: %s", str(e))
        return False
