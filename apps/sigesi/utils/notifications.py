import logging
from channels.layers import get_channel_layer
from django.utils import timezone
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


# Nombre del grupo Channel Layer al que se suscribe PermisosConsumer por
# usuario. Coincide con el usado en ``apps.sigesi/consumers.py`` (constructor
# ``self.group_name = f'permisos_user_{self.user_id}'``) y se conserva por
# compatibilidad con clientes ya suscritos; el consumer ahora emite también el
# tipo de evento ``evento_notification`` en este mismo grupo.
GROUP_PERMISOS_TEMPLATE = 'permisos_user_{user_id}'

# Tipo de evento que el consumer reenvía como ``evento_notification`` en
# notif_evento. Las vistas lo incluyen en el ``type`` del ``group_send``.
EVENTO_NOTIFICATION_TYPE = 'evento_notification'


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
        group_name = GROUP_PERMISOS_TEMPLATE.format(user_id=user_id)
        
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


# =====================================================================
# Notificaciones de eventos del flujo académico
# (Convocatoria / Postulación / ParticipaciónEvento)
# =====================================================================

def _push_event_notification(user_id, notificacion):
    """Envía por canal WebSocket el evento ``evento_notification`` a un usuario.

    ``notificacion`` es un dict ligero (no un modelo serializado) que se
    reenvía al cliente para refrescar su bandeja en tiempo real. **Falla en
    silencio** (solo loguea): la notificación ya quedó persistida, por lo que
    una falla de push no debe romper el flujo de la petición que la generó.
    """
    try:
        channel_layer = get_channel_layer()
        group_name = GROUP_PERMISOS_TEMPLATE.format(user_id=user_id)
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': EVENTO_NOTIFICATION_TYPE,
                'notificacion': notificacion,
                'timestamp': timezone.now().isoformat(),
            },
        )
    except Exception as e:
        logger.error(
            f"Error al hacer push de evento_notification al usuario {user_id}: {e}")


def _serialize_notificacion(notif):
    """Devuelve el dict ligero que viaja al cliente vía WebSocket.

    Incluye un ``target`` mínimo ``{kind, id}`` resuelto a partir del
    ``content_type``; el cliente puede refetch el detalle por su endpoint
    REST correspondiente.
    """
    return {
        'id': notif.id,
        'tipo': notif.tipo,
        'titulo': notif.titulo,
        'mensaje': notif.mensaje,
        'leida': notif.leida,
        'created_at': notif.created_at.isoformat() if notif.created_at else None,
        'target': (
            {'kind': notif.content_type.model, 'id': notif.object_id}
            if notif.content_type_id and notif.object_id else None
        ),
    }


def notificar_evento_a_usuarios(usuarios_qs, *, tipo, titulo, mensaje, target=None):
    """Crea (idempotente) una notificación por usuario y la empuja por WS.

    Args:
        usuarios_qs: queryset/iterable de ``User`` destinatarios.
        tipo: valor de ``Notificacion.TipoChoices`` (p. ej. ``'convocatoria_creada'``).
        titulo: encabezado corto (se muestra en la lista y en el toast).
        mensaje: cuerpo legible.
        target: instancia modelo opcional (Convocatoria, Postulacion,
            ParticipacionEvento, …). Se resuelve su ``content_type`` para
            soportar dedupe por ``(usuario, tipo, content_type, object_id)``
            y para que el cliente pueda navegar al detalle.

    Returns:
        Lista de ``Notificacion`` creadas (vacía si todos los destinatarios ya
        tenían la misma notificación por dedupe).
    """
    from django.contrib.contenttypes.models import ContentType
    from apps.sigesi.models import Notificacion

    ct = None
    obj_id = None
    if target is not None:
        ct = ContentType.objects.get_for_model(target.__class__)
        obj_id = target.pk

    creadas = []
    for usuario in usuarios_qs:
        defaults = {
            'titulo': titulo,
            'mensaje': mensaje,
            'leida': False,
        }
        # Dedupe: el mismo evento dirigido al mismo usuario una sola vez.
        lookup = {
            'usuario': usuario,
            'tipo': tipo,
            'content_type': ct,
            'object_id': obj_id,
        }
        notif, created = Notificacion.objects.update_or_create(
            defaults=defaults, **lookup)
        if created:
            _push_event_notification(usuario.id, _serialize_notificacion(notif))
        creadas.append(notif)
    return creadas


def _resolve_recipients_convocatoria(*, excluir=None):
    """Devuelve los usuarios con rol ``director_semillero`` activos.

    Excluye al actor cuando se pasa ``excluir`` para evitar la auto-notificación
    (p. ej. un director_semillero que crea una convocatoria en su nombre).
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    qs = User.objects.filter(
        roles__contains=['director_semillero'], is_active=True)
    if excluir is not None:
        qs = qs.exclude(pk=excluir.pk)
    return qs


def _resolve_recipients_postulacion(postulacion):
    """Devuelve los estudiantes matriculados en la postulación.

    Se excluye al actor cuando coincide con uno de los destinatarios (p. ej.
    un estudiante que crea su propia postulación, en flujos donde aplique).
    """
    return postulacion.estudiantes.all()


def _resolve_recipients_participacion(participacion):
    """Devuelve el participante de la participación (un único ``User``)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.filter(pk=participacion.participante_id)
