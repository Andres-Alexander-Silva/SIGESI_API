# Configuración de WebSockets en Render

## Cambios Realizados

✅ **Procfile** - Actualizado para usar Daphne en lugar de Gunicorn
✅ **settings.py** - Configuración mejorada de CHANNEL_LAYERS para Render

## ⚙️ Pasos de Configuración en Render

### 1. Crear Redis en Render

1. Ve a tu dashboard de Render: https://dashboard.render.com/
2. Haz clic en **New +** → **Redis**
3. Configura:
   - **Name**: `sigesi-redis` (o el nombre que prefieras)
   - **Region**: Selecciona la misma región que tu API
   - **Eviction Policy**: `noeviction` (recomendado)
4. Haz clic en **Create Redis**
5. Copia la **Internal Redis URL** (similar a: `redis://:xxxxx@xxxxx.c1.us-east-1.render.com:xxxxx`)

### 2. Agregar Variables de Entorno

En tu servicio web en Render:

1. Ve a **Settings** → **Environment**
2. Agrega las siguientes variables:

```
RENDER=true
REDIS_URL=redis://:password@hostname:port
DEBUG=false
SECRET_KEY=tu_secret_key_aqui
DB_NAME=tu_db_name
DB_USER=tu_db_user
DB_PASSWORD=tu_db_password
DB_HOST=tu_db_host
DB_PORT=5432
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
CORS_ALLOWED_ORIGINS=https://tudominio.com,https://www.tudominio.com
```

**IMPORTANTE**: 
- `REDIS_URL` debe ser la URL completa de tu Redis en Render
- Reemplaza `tudominio.com` con tu dominio actual
- Asegúrate que `CORS_ALLOWED_ORIGINS` incluya todos tus dominios del frontend

### 3. Actualizar el Build Script

El `build.sh` ya está configurado correctamente, pero verifica que tiene:

```bash
#!/usr/bin/env bash
set -o errexit

echo "==> Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo "==> Build completado!"
```

### 4. Actualizar el Procfile (ya hecho)

Tu Procfile ahora usa Daphne:

```
web: daphne -b 0.0.0.0 -p $PORT config.asgi:application
```

### 5. Hacer Push de los Cambios

```bash
git add .
git commit -m "chore: Configure WebSockets for Render with Daphne and Redis"
git push origin main  # o tu rama
```

Render automáticamente hará el deploy cuando detecte cambios.

## 🔍 Verificar que Funciona

1. Una vez que Render termine de desplegar, ve a tus **Logs**
2. Busca mensajes como:
   - `Application startup complete`
   - No debería haber errores de conexión a Redis

3. Prueba el WebSocket desde tu frontend:
```javascript
const userId = 1;
const wsUrl = `wss://tudominio.com/ws/permisos/${userId}/`;
const ws = new WebSocket(wsUrl);

ws.onopen = () => console.log('Conectado a WebSocket');
ws.onerror = (e) => console.error('Error:', e);
```

## ⚠️ Problemas Comunes

### "Channel layer is not configured"
- ❌ Redis URL no configurada correctamente
- ✅ Verifica que `REDIS_URL` esté en las variables de entorno de Render
- ✅ Asegúrate que Redis está en el mismo proyecto o accesible

### "Connection refused to Redis"
- ❌ Redis no está ejecutándose o no está accesible
- ✅ Verifica en Render que el servicio Redis esté `Available`
- ✅ Comprueba que usas la **Internal Redis URL**, no la Externa

### WebSocket cierra inmediatamente
- ❌ El usuario no está autenticado
- ✅ Verifica que el token JWT es válido
- ✅ Revisa los logs de Render para más detalles

### Timeout en WebSocket
- ❌ Daphne no está escuchando correctamente
- ✅ Verifica el Procfile usa `daphne -b 0.0.0.0 -p $PORT`
- ✅ Busca errores de binding en los logs

## 📊 Monitoreo

En Render, puedes:

1. **Ver Logs**:
   - Ve a tu servicio → **Logs**
   - Busca errores de conexión o canales

2. **Monitorear Redis**:
   - Ve a tu servicio Redis → **Info**
   - Verifica memoria y conexiones

3. **Monitorear el Servidor Web**:
   - Ve a tu servicio web → **Metrics**
   - Observa CPU, memoria y conexiones

## 🚀 Optimizaciones para Producción

```python
# En config/settings.py, para mejor rendimiento:
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [config('REDIS_URL')],
            'ssl_certfile': None,
            'ssl_keyfile': None,
            'ssl_cert_reqs': None,
            # Optimizaciones
            'capacity': 1500,
            'expiry': 10,
            'group_expiry': 86400,
            'receive_buffer_size': 524288,
        },
    },
}
```

## 💡 Alternativas a Redis en Render

Si no quieres crear un servicio Redis separado, puedes usar:

### Opción 1: PostgreSQL como Channel Layer (simple pero lento)
```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}
```
⚠️ **No recomendado para producción**

### Opción 2: Redis Cloud (servicio externo)
1. Ve a https://redis.com/try-free/
2. Crea una cuenta y un cluster Redis gratuito
3. Usa la URL de Redis Cloud en `REDIS_URL`

### Opción 3: Upstash Redis (excelente para Render)
1. Ve a https://upstash.com/
2. Crea un base de datos Redis
3. Usa la URL de Upstash en `REDIS_URL`

## Verificación Final

Después del deploy:

```bash
# 1. Verifica que la API responde
curl https://tudominio.com/api/v1/health/

# 2. Prueba WebSocket (desde el navegador, en consola):
const ws = new WebSocket('wss://tudominio.com/ws/permisos/1/');
ws.onopen = () => {
  console.log('✅ WebSocket conectado');
  ws.send(JSON.stringify({action: 'request_permisos'}));
};
ws.onmessage = (e) => console.log('Mensaje:', JSON.parse(e.data));
ws.onerror = (e) => console.error('❌ Error:', e);

# 3. Actualiza un permiso en la API y verifica la notificación en WebSocket
```

¡Listo! Tu API debe estar funcionando con WebSockets en Render.
