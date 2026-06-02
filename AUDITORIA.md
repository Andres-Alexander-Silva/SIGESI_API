# Auditoría y Registro Operacional del Sistema — Handoff

Traza histórica institucional de la actividad de los usuarios autenticados:
**quién** hizo **qué**, sobre **qué módulo**, con **qué rol activo** y **cuándo**.
Las filas se generan automáticamente vía middleware; se consultan por un endpoint
de solo lectura restringido al administrador.

> Convención del repo respetada: todo vive bajo `apps/sigesi/`, `models.py` único,
> split por capa (`config/`). El endpoint quedó en la capa administrativa `config/`,
> no en la URL literal `/api/auditoria/logs/` del requerimiento, para no romper el
> prefijo `/api/v1/<capa>/`.

---

## 1. Endpoint

| Método | Ruta | Acceso | Descripción |
|--------|------|--------|-------------|
| `GET` | `/api/v1/config/auditoria/logs/` | **Solo administrador** | Lista paginada de la traza, sobre `{success, data}` |
| `GET` | `/api/v1/config/auditoria/logs/{id}/` | **Solo administrador** | Detalle de un registro |

**Filtros** (query params): `?accion=&modulo=&usuario_email=&rol_activo=`
(además `?ordering=` y `?search=` por los backends globales de DRF).

### Respuesta (lista)

```json
{
  "success": true,
  "data": {
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": 1,
        "accion": "eliminacion",
        "modulo": "actividades",
        "usuario": "admin@ufps.edu.co",
        "rol_activo": "administrador",
        "metodo_http": "DELETE",
        "ruta": "/api/v1/core/actividades/7/",
        "status_code": 204,
        "object_id": "7",
        "ip": "127.0.0.1",
        "user_agent": "...",
        "fecha": "2026-06-01T14:32:10Z"
      }
    ]
  }
}
```

El campo `usuario` es el correo *snapshot* (`usuario_email`); los tres campos del
ejemplo del requerimiento (`accion`, `modulo`, `usuario`) siempre están presentes,
el resto enriquece la trazabilidad. La paginación es la global (`PAGE_SIZE=10`);
sin paginación `data` sería directamente la lista.

---

## 2. Qué se registra (y qué no)

El middleware audita en la **fase de respuesta**, según esta política acordada:

| Caso | ¿Se audita? | `accion` |
|------|-------------|----------|
| `POST` con `status < 400` | ✅ | `creacion` |
| `PUT` / `PATCH` con `status < 400` | ✅ | `actualizacion` |
| `DELETE` con `status < 400` | ✅ | `eliminacion` |
| `login` / `select-role` / `refresh` con `200` | ✅ | `autenticacion` |
| `GET` (lecturas) | ❌ | — |
| Cualquier escritura con `status >= 400` (400/403/...) | ❌ | — |
| Rutas excluidas (`/swagger/`, `/redoc/`, `/api/v1/ping/`, `/api/v1/health/`, el propio `/api/v1/config/auditoria/`) | ❌ | — |

> El choice `consulta` (GET) existe en el modelo pero **no se usa**. Reactivar el
> registro de lecturas es solo ampliar el filtro de método en el middleware.

---

## 3. Cómo funciona (decisión de diseño clave)

`AuditoriaMiddleware` es un **middleware real de Django** (registrado al final de
`settings.MIDDLEWARE`, para correr con el `status_code` final). Esto contrasta con
`apps/sigesi/middleware/authentication_middleware.py`, que **pese a su carpeta es la
clase de autenticación de DRF**, no un middleware.

**Landmine que condiciona todo:** DRF **no** escribe el usuario autenticado de
vuelta en el `HttpRequest` de Django. Por eso el middleware **no** puede leer
`request.user`; en su lugar identifica al usuario y su **rol activo** decodificando
el `Bearer` JWT por su cuenta:

- Escrituras → decodifica el header `Authorization` (claims `user_id`, `role`).
- `login` (no hay `Bearer` entrante) → decodifica el access token de la **respuesta**
  (clave `token`, no `access`); `select-role`/`refresh` usan el token entrante o el
  de la respuesta.

El middleware **nunca lanza**: toda la escritura va en `try/except` con `logging`,
de modo que un fallo de auditoría jamás afecta la respuesta al cliente.

---

## 4. Archivos

| Archivo | Rol |
|---------|-----|
| `apps/sigesi/models.py` (sección `AUDITORÍA Y TRAZABILIDAD`) | Modelo `RegistroAuditoria` |
| `apps/sigesi/migrations/0028_registroauditoria.py` | Migración del modelo |
| `apps/sigesi/utils/auditoria.py` | Lógica compartida: decode de token, `resolver_modulo`, `registrar()`, listas de rutas |
| `apps/sigesi/middleware/audit_middleware.py` | `AuditoriaMiddleware` (orquestación) |
| `config/settings.py` | Registro del middleware (al final de `MIDDLEWARE`) |
| `apps/sigesi/decorators/permissions.py` | `AuditoriaPermission` (solo admin) |
| `apps/sigesi/serializers/config/auditoria_serializer.py` | `RegistroAuditoriaSerializer` (solo lectura) |
| `apps/sigesi/views/config/auditoria_view.py` | `RegistroAuditoriaViewSet` (list/retrieve, sobre `{success, data}`) |
| `apps/sigesi/routers/config/auditoria_urls.py` | Router → `auditoria/logs/` |
| `config/urls.py` | `include(...auditoria_urls)` en la capa `config/` |
| `apps/sigesi/tests/test_auditoria.py` | Tests (JWT real) |

---

## 5. Modelo `RegistroAuditoria`

| Campo | Tipo | Notas |
|-------|------|-------|
| `usuario` | FK User, **`SET_NULL`** | La traza sobrevive al borrado del usuario |
| `usuario_email` | `CharField` | *Snapshot* del correo (institucional → personal); es `usuario` en la respuesta |
| `rol_activo` | `CharField` | Claim `role` del token (rol activo) |
| `accion` | `CharField` choices | `acceso`/`autenticacion`/`creacion`/`actualizacion`/`eliminacion`/`consulta` |
| `modulo` | `CharField` | Slug del recurso, inferido de la URL |
| `metodo_http`, `ruta`, `status_code` | — | Metadatos de la petición |
| `object_id` | `CharField` (blank) | PK del recurso si se infiere de la URL |
| `ip`, `user_agent` | — | Origen de la petición |
| `fecha` | `DateTimeField(auto_now_add, db_index)` | Orden por defecto: `-fecha` |

Índices: `accion`, `modulo`, `usuario`.

---

## 6. Verificación

### Migración
```powershell
.venv\Scripts\python manage.py migrate   # ya aplicada: 0028_registroauditoria
```

### Manual (Swagger / cliente)
1. `POST /api/v1/auth/login/` como admin → tomar `token` (rol único auto-selecciona;
   multi-rol requiere `POST /api/v1/auth/select-role/`).
2. Ejecutar una escritura, p. ej. `DELETE /api/v1/core/actividades/{id}/` con
   `Authorization: Bearer <token>`.
3. `GET /api/v1/config/auditoria/logs/` → confirmar la fila `eliminacion` /
   `actividades` / correo del admin.
4. Repetir el `GET` con un token de **estudiante** → `403`.

### Tests
> Política del repo: los tests **no** se corren automáticamente. **Importante:** estos
> usan **JWT real** (`build_context_tokens` + `credentials`), no el fixture
> `auth_client` (`force_authenticate`), porque ese no envía token y no ejercitaría
> el middleware.

```powershell
.venv\Scripts\python -m pytest apps/sigesi/tests/test_auditoria.py
# Tras una migración, la primera corrida puede requerir:
.venv\Scripts\python -m pytest apps/sigesi/tests/test_auditoria.py --create-db
```

Casos cubiertos: escritura genera registro (creación/eliminación con módulo, correo
y rol correctos) · GET y escrituras 403 **no** generan registro · login genera
`autenticacion` · admin obtiene el sobre `{success, data}` · 403 para estudiante,
director_grupo, director_semillero y líder estudiantil · el propio endpoint no se
autoaudita.

---

## 7. Notas / extensiones futuras

- **Volumen:** una fila `INSERT` síncrona por escritura. Si crece, mover
  `registrar()` a un `@shared_task` de Celery (mismo patrón que el envío de correo
  en `utils/email_service.py`) es un cambio aislado.
- **Retención:** no hay poda automática. Si se habilita el registro de `GET`
  (`consulta`), conviene añadir un job de retención/limpieza.
- **Intentos denegados:** hoy las escrituras `>= 400` no se registran. Para
  monitoreo de seguridad podría auditarse el `401/403` con una `accion` propia
  (cambio acotado en `AuditoriaMiddleware._auditar`).
