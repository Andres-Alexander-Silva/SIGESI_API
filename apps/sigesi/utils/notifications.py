import logging
from channels.layers import get_channel_layer
from django.utils import timezone
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


def notificar_actualizacion_permisos(user_id, roles=None, menus_data=None, mensaje="Tu acceso ha sido actualizado"):
    """
    Envía una notificación en tiempo real a un usuario sobre la actualización de sus permisos.
    
    Args:
        user_id: ID del usuario a notificar
        roles: Lista de roles del usuario (opcional)
        menus_data: Datos de menús y permisos actualizados (opcional)
        mensaje: Mensaje descriptivo de la notificación
        
    Returns:
        bool: True si la notificación se envió exitosamente
    """
    try:
        channel_layer = get_channel_layer()
        group_name = f'permisos_user_{user_id}'
        
        # Crear el payload de la notificación
        event_data = {
            'type': 'permisos_update',
            'message': mensaje,
            'data': {
                'roles': roles or [],
                'menus': menus_data or [],
            },
            'timestamp': timezone.now().isoformat(),
        }
        
        # Enviar el evento al grupo usando async_to_sync
        async_to_sync(channel_layer.group_send)(
            group_name,
            event_data
        )
        
        logger.info(f"Notificación de permisos enviada al usuario {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error al enviar notificación de permisos: {str(e)}")
        return False


def obtener_permisos_usuario(user):
    """
    Obtiene los permisos actualizados del usuario en el mismo formato que el endpoint mis_permisos.
    
    Args:
        user: Instancia del modelo User
        
    Returns:
        dict: Diccionario con roles y menus serializados
    """
    try:
        from apps.sigesi.models import Menu
        from apps.sigesi.serializers.config.user_serializer import MenuPerfilSerializer
        
        menus = Menu.objects.filter(
            estado=True,
            opciones__estado=True,
            opciones__permisos__rol__in=user.roles,
        ).distinct()

        serializer = MenuPerfilSerializer(
            menus, many=True, context={'roles': user.roles}
        )
        menus_data = [m for m in serializer.data if m['opciones']]
        
        return {
            'roles': user.roles,
            'menus': menus_data,
        }
    except Exception as e:
        logger.error(f"Error obteniendo permisos del usuario {user.id}: {str(e)}")
        return {
            'roles': user.roles,
            'menus': [],
        }


def notificar_cambio_permiso(permiso_obj):
    """
    Notifica al usuario cuyo rol fue modificado cuando se actualiza un permiso.
    
    Args:
        permiso_obj: Instancia del modelo Permiso que fue actualizada
    """
    try:
        # Obtener todos los usuarios que tienen este rol en su lista de roles
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        usuarios_rol = User.objects.filter(roles__contains=[permiso_obj.rol], is_active=True)
        
        for usuario in usuarios_rol:
            # Obtener los permisos actualizados del usuario
            permisos_data = obtener_permisos_usuario(usuario)
            
            # Enviar notificación
            notificar_actualizacion_permisos(
                user_id=usuario.id,
                roles=usuario.roles,
                menus_data=permisos_data['menus'],
                mensaje=f"Tu acceso a '{permiso_obj.opcion.nombre}' ha sido actualizado"
            )
            
    except Exception as e:
        logger.error(f"Error al notificar cambio de permiso: {str(e)}")


def notificar_cambios_permisos_multiples(rol):
    """
    Notifica a todos los usuarios con un rol específico sobre cambios en sus permisos.
    Obtiene y envía los permisos actualizados en el mismo formato que mis_permisos.
    
    Args:
        rol: El rol cuya configuración de permisos cambió
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        usuarios_rol = User.objects.filter(roles__contains=[rol], is_active=True)
        
        for usuario in usuarios_rol:
            # Obtener los permisos actualizados del usuario
            permisos_data = obtener_permisos_usuario(usuario)
            
            # Enviar notificación con los permisos actualizados
            notificar_actualizacion_permisos(
                user_id=usuario.id,
                roles=usuario.roles,
                menus_data=permisos_data['menus'],
                mensaje="La configuración de permisos de tu rol ha sido actualizada"
            )
            
    except Exception as e:
        logger.error(f"Error al notificar cambios de permisos múltiples: {str(e)}")
