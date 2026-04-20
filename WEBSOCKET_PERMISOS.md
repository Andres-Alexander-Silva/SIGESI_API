# WebSocket de Permisos en Tiempo Real

## Descripción

Sistema de notificaciones en tiempo real para cambios de permisos usando Django Channels y WebSockets.

## Archivos Creados/Modificados

### Backend

1. **requirements.txt** - Agregadas dependencias:
   - `channels==4.0.0`
   - `channels-redis==4.1.0`
   - `daphne` (ASGI server)
   - `redis==5.0.1`

2. **config/asgi.py** - Configurado ASGI con Channels para WebSockets

3. **config/settings.py** - Agregadas configuraciones:
   - `ASGI_APPLICATION = 'config.asgi.application'`
   - `CHANNEL_LAYERS` para Redis
   - Apps: `'daphne'` y `'channels'`

4. **apps/sigesi/consumers.py** - Nuevo archivo con:
   - `PermisosConsumer` - Maneja conexiones WebSocket
   - Métodos de conexión, desconexión y recepción de mensajes
   - Serialización de permisos en tiempo real

5. **apps/sigesi/utils/notifications.py** - Nuevas funciones:
   - `notificar_actualizacion_permisos()` - Envía notificaciones a usuarios
   - `notificar_cambio_permiso()` - Notifica cambios de permisos
   - `notificar_cambios_permisos_multiples()` - Notifica cambios de rol

6. **apps/sigesi/views/config/rbac_view.py** - Modificada la clase `PermisoViewSet`:
   - `perform_create()` - Notifica al crear permiso
   - `perform_update()` - Notifica al actualizar permiso
   - `perform_partial_update()` - Notifica al actualizar parcialmente
   - `perform_destroy()` - Notifica al eliminar permiso

## Configuración de Redis

Para que los WebSockets funcionen, necesitas tener Redis ejecutándose:

```bash
# En macOS con Homebrew
brew install redis
brew services start redis

# Verificar que está corriendo
redis-cli ping
# Respuesta: PONG
```

## Uso desde el Frontend

### Conexión WebSocket

```javascript
// Conectar al WebSocket
const userId = 1; // ID del usuario autenticado
const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const wsUrl = `${protocol}://${window.location.host}/ws/permisos/${userId}/`;
const webSocket = new WebSocket(wsUrl);

// Manejar conexión
webSocket.onopen = (event) => {
  console.log('Conectado a WebSocket de permisos');
  
  // Solicitar permisos iniciales (opcional)
  webSocket.send(JSON.stringify({
    action: 'request_permisos'
  }));
};

// Manejar mensajes
webSocket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'permisos_update') {
    console.log('Actualización de permisos:', data);
    
    if (data.action === 'update') {
      // Permisos del usuario fueron actualizados
      console.log('Mensaje:', data.message);
      console.log('Nuevos permisos:', data.data);
      
      // Actualizar el menú del usuario
      actualizarMenuUsuario(data.data);
      
      // Mostrar notificación al usuario
      mostrarNotificacion(data.message);
    } else if (data.action === 'response') {
      // Respuesta a solicitud de permisos
      console.log('Permisos del usuario:', data.data);
    }
  }
};

// Manejar errores
webSocket.onerror = (error) => {
  console.error('Error en WebSocket:', error);
};

// Manejar desconexión
webSocket.onclose = (event) => {
  console.log('Desconectado de WebSocket');
};
```

### Ejemplo con React

```jsx
import { useEffect, useRef, useState } from 'react';

export function PermisosConectados() {
  const [permisos, setPermisos] = useState(null);
  const webSocketRef = useRef(null);

  useEffect(() => {
    const userId = localStorage.getItem('user_id'); // O desde el contexto
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${window.location.host}/ws/permisos/${userId}/`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('Conectado a WebSocket de permisos');
      // Solicitar permisos iniciales
      ws.send(JSON.stringify({ action: 'request_permisos' }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'permisos_update' && data.action === 'update') {
        console.log('Permisos actualizados:', data.data);
        setPermisos(data.data);
        
        // Aquí puedes:
        // - Actualizar el estado de la navegación
        // - Mostrar un toast de notificación
        // - Recargar componentes que dependan de los permisos
      }
    };

    ws.onerror = (error) => {
      console.error('Error en WebSocket:', error);
    };

    webSocketRef.current = ws;

    return () => {
      if (webSocketRef.current) {
        webSocketRef.current.close();
      }
    };
  }, []);

  return null; // O un componente de estado
}
```

### Ejemplo con Vue.js

```vue
<script setup>
import { onMounted, onUnmounted, ref } from 'vue';

const permisos = ref(null);
let webSocket = null;

onMounted(() => {
  const userId = localStorage.getItem('user_id');
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const wsUrl = `${protocol}://${window.location.host}/ws/permisos/${userId}/`;

  webSocket = new WebSocket(wsUrl);

  webSocket.onopen = () => {
    console.log('Conectado a WebSocket de permisos');
    webSocket.send(JSON.stringify({ action: 'request_permisos' }));
  };

  webSocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'permisos_update') {
      console.log('Notificación:', data.message);
      permisos.value = data.data;
    }
  };
});

onUnmounted(() => {
  if (webSocket) {
    webSocket.close();
  }
});
</script>
```

## Flujo de Actualización de Permisos

```
1. Admin actualiza un permiso en la API
   ↓
2. Vista PermisoViewSet.partial_update() se ejecuta
   ↓
3. Llama a perform_partial_update()
   ↓
4. Llama a notificar_cambios_permisos_multiples(rol)
   ↓
5. Se obtienen todos los usuarios con ese rol
   ↓
6. Para cada usuario, se envía un evento a su grupo de WebSocket
   ↓
7. PermisosConsumer recibe el evento en "permisos_update"
   ↓
8. Se serializa nuevamente los permisos del usuario
   ↓
9. El WebSocket envía el mensaje al cliente
   ↓
10. Frontend recibe la actualización en tiempo real
```

## Configuración de Variables de Entorno

Agrega estas variables a tu archivo `.env`:

```bash
# Redis (para desarrollo local)
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Redis (para producción, si usas Redis URL)
# REDIS_URL=redis://usuario:contraseña@host:puerto

# Channels
CHANNEL_LAYERS_BACKEND=channels_redis.core.RedisChannelLayer
```

## Inicio del Servidor

Para desarrollo, usa Daphne en lugar de Gunicorn:

```bash
# Desarrollo con Daphne
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# O con punto de entrada automático
python manage.py runserver
# Django detectará ASGI automáticamente en desarrollo
```

## Pruebas

### Test de WebSocket con WebSocket Client

```bash
pip install websocket-client

python -c "
import websocket
import json

ws = websocket.WebSocket()
ws.connect('ws://localhost:8000/ws/permisos/1/')
print('Conectado')

# Solicitar permisos
ws.send(json.dumps({'action': 'request_permisos'}))
print(ws.recv())

ws.close()
"
```

## Troubleshooting

### Redis no se conecta
```bash
# Verificar que Redis está corriendo
redis-cli ping

# Si no funciona, iniciar Redis
redis-server
```

### WebSocket cierra inmediatamente
- Verifica que el usuario está autenticado
- Comprueba que el token JWT es válido
- Revisa los logs de Django para errores

### No se reciben notificaciones
- Asegúrate que Redis está ejecutándose
- Verifica que CHANNEL_LAYERS está configurado correctamente
- Revisa los logs de Daphne/Django

## Rendimiento

Para producción:

1. **Usa un servicio Redis dedicado** (Redis Cloud, AWS ElastiCache)
2. **Escala con múltiples workers Daphne**
3. **Considera usar un balanceador de carga**
4. **Monitorea la conexión de canales**

## Seguridad

- Las conexiones WebSocket requieren autenticación JWT
- Solo los usuarios autenticados pueden conectarse
- Cada usuario solo recibe sus propias notificaciones
- El `user_id` en la URL debe coincidir con el usuario autenticado
