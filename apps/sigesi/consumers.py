import json
import logging
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class PermisosConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer para notificaciones en tiempo real de cambios de permisos.
    
    Clientes se conectan a: ws://hostname/ws/permisos/<user_id>/?token=<jwt_token>
    
    El token JWT se pasa en la query string.
    Cuando se actualiza un permiso, se envía un mensaje a todos los usuarios afectados.
    """

    async def connect(self):
        """Maneja la conexión WebSocket."""
        try:
            self.user_id = self.scope['url_route']['kwargs']['user_id']
            
            # Extraer token de la query string
            query_string = self.scope.get('query_string', b'').decode('utf-8')
            query_params = parse_qs(query_string)
            token = query_params.get('token', [None])[0]
            
            # Validar token JWT y obtener usuario
            self.user = await self._validate_token_and_get_user(token, self.user_id)
            
            if not self.user:
                logger.warning(f"Token inválido o usuario no existe: user_id={self.user_id}")
                await self.close(code=4001, reason="Token inválido o usuario no autenticado")
                return
            
            # Crear nombre único de grupo por usuario
            self.group_name = f'permisos_user_{self.user_id}'
            
            # Agregar el consumidor al grupo
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            await self.accept()
            logger.info(f"✅ Usuario {self.user_id} ({self.user.username}) conectado a WebSocket de permisos")
            
        except Exception as e:
            logger.error(f"❌ Error en conexión WebSocket: {str(e)}")
            await self.close()

    async def disconnect(self, close_code):
        """Maneja la desconexión WebSocket."""
        try:
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(
                    self.group_name,
                    self.channel_name
                )
            logger.info(f"Usuario {self.user_id} desconectado de WebSocket de permisos")
        except Exception as e:
            logger.error(f"Error en desconexión WebSocket: {str(e)}")

    async def receive(self, text_data):
        """
        Maneja mensajes recibidos del cliente.
        El cliente puede enviar un mensaje para solicitar sus permisos actualizados.
        """
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'request_permisos':
                # Cliente solicita sus permisos actuales
                permisos_data = await self._get_user_permisos(self.user_id)
                await self.send(text_data=json.dumps({
                    'type': 'permisos_update',
                    'action': 'response',
                    'data': permisos_data,
                }))
                
        except json.JSONDecodeError:
            logger.warning(f"Mensaje JSON inválido recibido de {self.user_id}")
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")

    async def permisos_update(self, event):
        """
        Manejador de evento que recibe notificaciones de actualizaciones de permisos.
        Este método es llamado por el group_send desde la vista.
        """
        try:
            # Enviar el mensaje al cliente WebSocket
            await self.send(text_data=json.dumps({
                'type': 'permisos_update',
                'action': 'update',
                'message': event.get('message', 'Tus permisos han sido actualizados'),
                'data': event.get('data', {}),
                'timestamp': event.get('timestamp'),
            }))
            logger.info(f"📤 Notificación de permisos enviada a {self.user_id}")
        except Exception as e:
            logger.error(f"Error enviando notificación: {str(e)}")

    @database_sync_to_async
    def _validate_token_and_get_user(self, token, user_id):
        """
        Valida el token JWT y retorna el usuario si es válido.
        
        Args:
            token: Token JWT
            user_id: ID del usuario que debe coincidir con el token
            
        Returns:
            User: Instancia del usuario si el token es válido, None en caso contrario
        """
        try:
            if not token:
                logger.warning("No token provided for WebSocket connection")
                return None
            
            # Validar token JWT
            from rest_framework_simplejwt.tokens import AccessToken
            from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
            
            try:
                access_token = AccessToken(token)
                user_id_from_token = access_token['user_id']
                
                # Verificar que el user_id de la URL coincide con el del token
                if str(user_id_from_token) != str(user_id):
                    logger.warning(f"User ID mismatch: {user_id_from_token} != {user_id}")
                    return None
                
                # Obtener el usuario
                user = User.objects.get(id=user_id_from_token)
                if not user.is_active:
                    logger.warning(f"Usuario inactivo: {user_id_from_token}")
                    return None
                    
                logger.info(f"✓ Token válido para usuario {user.username}")
                return user
                
            except (InvalidToken, TokenError) as e:
                logger.warning(f"Token inválido: {str(e)}")
                return None
                
        except User.DoesNotExist:
            logger.warning(f"Usuario no existe: {user_id}")
            return None
        except Exception as e:
            logger.error(f"Error validando token: {str(e)}")
            return None

    @database_sync_to_async
    def _get_user(self, user_id):
        """Obtener usuario desde la base de datos de forma asincrónica."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def _get_user_permisos(self, user_id):
        """Obtener permisos actualizados del usuario."""
        try:
            user = User.objects.get(id=user_id)
            from apps.sigesi.models import Menu
            
            menus = Menu.objects.filter(
                estado=True,
                opciones__estado=True,
                opciones__permisos__rol=user.rol,
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
                    permiso = opcion.permisos.filter(rol=user.rol).first()
                    if permiso:
                        menu_data['opciones'].append({
                            'id': opcion.id,
                            'nombre': opcion.nombre,
                            'url': opcion.url,
                            'puede_consultar': permiso.puede_consultar,
                            'puede_crear': permiso.puede_crear,
                            'puede_actualizar': permiso.puede_actualizar,
                            'puede_eliminar': permiso.puede_eliminar,
                        })
                
                if menu_data['opciones']:
                    menus_data.append(menu_data)
            
            return {
                'rol': user.rol,
                'menus': menus_data,
            }
        except User.DoesNotExist:
            return {}
