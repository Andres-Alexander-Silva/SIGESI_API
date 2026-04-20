import asyncio
import json
import logging
from channels.layers import get_channel_layer
from django.utils import timezone
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


def notificar_actualizacion_permisos(user_id, rol=None, menus_data=None, mensaje="Tu acceso ha sido actualizado"):
    """
    Envía una notificación en tiempo real a un usuario sobre la actualización de sus permisos.
    
    Args:
        user_id: ID del usuario a notificar
        rol: Rol del usuario (opcional)
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
                'rol': rol,
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


def notificar_cambio_permiso(permiso_obj):
    """
    Notifica al usuario cuyo rol fue modificado cuando se actualiza un permiso.
    
    Args:
        permiso_obj: Instancia del modelo Permiso que fue actualizada
    """
    try:
        # Obtener todos los usuarios con este rol
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        usuarios_rol = User.objects.filter(rol=permiso_obj.rol)
        
        for usuario in usuarios_rol:
            # Obtener los permisos actualizados del usuario
            from apps.sigesi.models import Menu
            
            menus = Menu.objects.filter(
                estado=True,
                opciones__estado=True,
                opciones__permisos__rol=usuario.rol,
            ).distinct()
            
            # Serializar los datos
            menus_data = []
            for menu in menus:
                menu_data = {
                    'id': menu.id,
                    'nombre': menu.nombre,
                    'icono': menu.icono,
                    'opciones': []
                }
                
                for opcion in menu.opciones.filter(estado=True):
                    perm = opcion.permisos.filter(rol=usuario.rol).first()
                    if perm:
                        menu_data['opciones'].append({
                            'id': opcion.id,
                            'nombre': opcion.nombre,
                            'url': opcion.url,
                            'puede_consultar': perm.puede_consultar,
                            'puede_crear': perm.puede_crear,
                            'puede_actualizar': perm.puede_actualizar,
                            'puede_eliminar': perm.puede_eliminar,
                        })
                
                if menu_data['opciones']:
                    menus_data.append(menu_data)
            
            # Enviar notificación
            notificar_actualizacion_permisos(
                user_id=usuario.id,
                rol=usuario.rol,
                menus_data=menus_data,
                mensaje=f"Tu acceso a '{permiso_obj.opcion.nombre}' ha sido actualizado"
            )
            
    except Exception as e:
        logger.error(f"Error al notificar cambio de permiso: {str(e)}")


def notificar_cambios_permisos_multiples(rol):
    """
    Notifica a todos los usuarios con un rol específico sobre cambios en sus permisos.
    
    Args:
        rol: El rol cuya configuración de permisos cambió
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        usuarios_rol = User.objects.filter(rol=rol, is_active=True)
        
        for usuario in usuarios_rol:
            notificar_actualizacion_permisos(
                user_id=usuario.id,
                rol=usuario.rol,
                mensaje="La configuración de permisos de tu rol ha sido actualizada"
            )
            
    except Exception as e:
        logger.error(f"Error al notificar cambios de permisos múltiples: {str(e)}")
