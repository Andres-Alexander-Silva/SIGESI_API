# Handoff — Notification alerts for the events workflow

Implementation handoff for the persistent + real-time notification feed that alerts
users to changes in the `Evento → Convocatoria → Postulación → ParticipaciónEvento`
chain (see [EVENTOS_WORKFLOW.md](EVENTOS_WORKFLOW.md)).

- **Branch:** `development`
- **Migration introduced:** `0027_notificacion.py`
- **Domain language:** Spanish (models, fields, messages — keep the convention).

---

## 1. Why this change

The events workflow had no notification system: a director_semillero who wanted to
know about a new Convocatoria had to poll the API; the estudiantes on a Postulación
didn't get an alert when it was approved/rejected; a participant in
`ParticipacionEvento` didn't get a notification when the certificate was uploaded.

Today the codebase had **real-time channels-layer push only**, for one narrow use
case (`PermisosConsumer` for permission-change notifications in
`apps/sigesi/consumers.py` + helpers in `apps/sigesi/utils/notifications.py`),
with **no persistent model**. This change adds a persistent `Notificacion` model +
REST list/mark-read endpoints, and reuses the **same** websocket group to push
the new `evento_notification` event — so clients can show an unread badge and a
"my notifications" view.

## 2. The notification shape

- **Model** — `Notificacion` (persistent) in `apps/sigesi/models.py`. Fields:
  `usuario` (FK to `User`), `tipo` (TextChoices: `convocatoria_creada`,
  `convocatoria_actualizada`, `postulacion_creada`, `postulacion_actualizada`,
  `participacion_creada`, `participacion_actualizada`), `titulo`, `mensaje`,
  `content_type`+`object_id` (GenericForeignKey to the source object),
  `leida`, `read_at`, `created_at`. Indexed on `(usuario, -created_at)` and
  `(usuario, leida)`. **`unique_together = (usuario, tipo, content_type, object_id)`**
  deduplicates replays of the same event.
- **REST** — `GET/PATCH/DELETE /api/v1/core/notificaciones/`, scoped to the
  authenticated user. Two `@action`s: `POST .../marcar-leida/` (single) and
  `POST .../marcar-todas-leidas/` (bulk, returns `{actualizadas: N}`).
- **WebSocket** — same route `ws/permisos/<user_id>/?token=<jwt>`; the consumer
  now handles a new `evento_notification` event type. The group name
  (`permisos_user_<id>`) is unchanged for backward compatibility.
- **Push** — fire-and-forget; failures are logged but **never** raised (the
  notification is already persisted). The only client-visible state is the DB row.

## 3. Trigger matrix (audience rules)

| Trigger | Audience | Push event | Notes |
|---------|----------|------------|-------|
| `ConvocatoriaViewSet.create` | All `director_semillero` users (actor excluded) | `convocatoria_creada` | New convocatoria is a public-to-directors call. |
| `ConvocatoriaViewSet.update` / `partial_update` | Same as above | `convocatoria_actualizada` | **Only when `estado` actually changes** (a PATCH that touches `descripcion` does NOT notify). |
| `PostulacionViewSet.create` | Every user in `postulacion.estudiantes` (actor excluded) | `postulacion_creada` | Estudiantes see "you've been postulated". |
| `PostulacionViewSet.update` / `partial_update` | Same audience | `postulacion_actualizada` | Only when `estado` changes. |
| `PostulacionViewSet.aprobar` / `rechazar` | Same audience | `postulacion_actualizada` | Resolver (admin / director_grupo) is excluded from the recipients. |
| `ParticipacionEventoViewSet.create` | `obj.participante` | `participacion_creada` | Self-registration excludes the actor. |
| `ParticipacionEventoViewSet.update` / `partial_update` | `obj.participante` | `participacion_actualizada` | Fires on **any** change (per the "every state change" answer). |
| `ParticipacionEventoViewSet.destroy` | `obj.participante` | `participacion_actualizada` | Uses a pre-delete snapshot since the row is gone. |
| `ParticipacionEventoViewSet.cargar_certificado` | `obj.participante` | `participacion_actualizada` | The certificate arriving is a meaningful state change for the participant. |

Recipient resolution lives in **one place per resource** in
`apps/sigesi/utils/notifications.py`:

- `_resolve_recipients_convocatoria(*, excluir=None)` — `User.objects.filter(roles__contains=['director_semillero'], is_active=True)`, excluding the actor.
- `_resolve_recipients_postulacion(postulacion)` — `postulacion.estudiantes.all()`.
- `_resolve_recipients_participacion(participacion)` — `User.objects.filter(pk=participacion.participante_id)`.

Centralizing the audience rules (mirrors `participantes_en_alcance` in
`utils/alcance.py`) keeps the three layers — serializer, view, permission — from
drifting.

## 4. Files changed / created

### Models & migration
- `apps/sigesi/models.py` — added `Notificacion` (NOTIFICACIONES section) plus
  imports for `ContentType`/`GenericForeignKey`.
- `apps/sigesi/migrations/0027_notificacion.py` — purely additive (new table, all
  nullable FKs, contenttypes dependency).

### Helpers (extend, don't create new file)
- `apps/sigesi/utils/notifications.py` — added `GROUP_PERMISOS_TEMPLATE`,
  `EVENTO_NOTIFICATION_TYPE`, `notificar_evento_a_usuarios`,
  `_push_event_notification`, `_serialize_notificacion`, and the three
  `_resolve_recipients_*` helpers. The existing `notificar_actualizacion_permisos`
  now uses the shared `GROUP_PERMISOS_TEMPLATE` constant.

### Consumer (extend, don't create new file)
- `apps/sigesi/consumers.py` — added `evento_notification` handler on
  `PermisosConsumer`. The existing `permisos_update` handler is untouched.

### New API stack
- `serializers/core/notificacion_serializer.py` — `NotificacionListSerializer`
  (exposes `target` as `{kind, id}`).
- `views/core/notificacion_view.py` — `NotificacionViewSet` (List/Retrieve/Destroy
  + `marcar-leida` + `marcar-todas-leidas` actions). `get_queryset` filters to
  the authenticated user.
- `routers/core/notificaciones_urls.py` — register `r'notificaciones'`.
- `config/urls.py` — registered under `/api/v1/core/`.

### Wired into the workflow views
- `views/core/convocatoria_view.py` — `create` always notifies; `update` /
  `partial_update` only when `estado` changes (helper `_emitir_actualizacion`).
- `views/core/postulacion_view.py` — `create` notifies estudiantes; `update` /
  `partial_update` only on `estado` change; `_resolver` (used by
  `aprobar`/`rechazar`) captures `estado_anterior` and notifies the estudiantes
  via the shared helper `_emitir_actualizacion_estado`.
- `views/core/participacion_evento_view.py` — `create`, `update`,
  `partial_update`, `destroy`, and `cargar_certificado` all notify the
  participant via the shared helper `_emitir_a_participante`.

### Docs
- `CLAUDE.md` — one-paragraph note added to the "Realtime permission updates
  (Channels)" section, naming the new `evento_notification` event and the dedupe
  rule.

### Tests
- `apps/sigesi/tests/test_notificaciones.py` (new) — covers all 9 trigger rows +
  the 4 REST cases (list scope, `?leida=` filter, `marcar-leida`,
  `marcar-todas-leidas`). Push via WS is mocked with
  `unittest.mock.patch('apps.sigesi.utils.notifications.async_to_sync')` — fire-
  and-forget, not exercised.

## 5. API surface

Base: `/api/v1/core/`

- `GET /notificaciones/` — own notifications; filters `?leida=&tipo=`.
- `GET /notificaciones/{id}/` — detail.
- `DELETE /notificaciones/{id}/` — delete one.
- `PATCH /notificaciones/{id}/marcar-leida/` — set `leida=True, read_at=now`.
- `POST /notificaciones/marcar-todas-leidas/` — bulk; returns `{actualizadas: N}`.
- No `POST /notificaciones/` (notifications are created internally only).

WS event format (server → client):

```json
{
  "type": "evento_notification",
  "action": "new",
  "notificacion": {
    "id": 42,
    "tipo": "postulacion_creada",
    "titulo": "Fuiste postulado a una convocatoria",
    "mensaje": "El semillero \"…\" te incluyó en la postulación a \"…\".",
    "leida": false,
    "created_at": "2026-06-01T12:34:56.789Z",
    "target": { "kind": "postulacion", "id": 7 }
  },
  "timestamp": "2026-06-01T12:34:56.789Z"
}
```

## 6. How to run / verify

```powershell
# Apply the migration
.\.venv\Scripts\python.exe manage.py migrate

# Tests (first run after the migration needs --create-db)
.\.venv\Scripts\python.exe -m pytest `
  apps/sigesi/tests/test_notificaciones.py `
  apps/sigesi/tests/test_convocatoria.py `
  apps/sigesi/tests/test_postulacion.py `
  apps/sigesi/tests/test_participacion_evento.py --create-db
```

Manual happy path via Swagger (`/swagger/`):
1. `POST /api/v1/core/eventos/` (admin).
2. `POST /api/v1/core/convocatorias/` (admin) — `director_semillero` receives a
   `convocatoria_creada` push on `ws/permisos/<id>/`.
3. `POST /api/v1/core/postulaciones/` (director_semillero) — estudiantes
   receive `postulacion_creada`.
4. `POST /api/v1/core/postulaciones/{id}/aprobar/` (director_grupo) — estudiantes
   receive `postulacion_actualizada`; resolver does NOT.
5. `POST /api/v1/core/participaciones-evento/` — participant receives
   `participacion_creada`.
6. `POST /api/v1/core/participaciones-evento/{id}/cargar-certificado/` —
   participant receives `participacion_actualizada` ("Tu certificado fue cargado").
7. `GET /api/v1/core/notificaciones/?leida=false` shows the inbox;
   `POST /api/v1/core/notificaciones/marcar-todas-leidas/` clears it.

Validated so far: `manage.py check` passes; the 48 tests in the four files
**collect** cleanly. Per repo policy the suite was **not executed** automatically
— run the command above.

## 7. Open decisions / follow-ups

- **Audience for Convocatoria changes** — currently all `director_semillero`
  users, not just the directors of semilleros that already have a `Postulacion`
  for that convocatoria. A more targeted audience would require an extra query
  per Convocatoria and is easy to swap in `_resolve_recipients_convocatoria` —
  the function is the single seam.
- **Notification preferences** — there is no per-user opt-out yet. If a user
  silences a notification type, a `NotificacionPreferencia` model with a
  `tipos_silenciados` array could short-circuit `notificar_evento_a_usuarios`
  before persistence. Not implemented.
- **Email follow-up** — notifications are in-app only. The
  `email_service.notificar_*_async` pattern in `utils/email_service.py` is
  reusable if you want to add a digest email for unread `postulacion_*` rows.
- **Target cleanup** — when a `Convocatoria` / `Postulacion` /
  `ParticipacionEvento` is deleted, the related `Notificacion` rows stay around
  (the `GenericForeignKey` nulls out `content_type`/`object_id` only on
  `SET_NULL`, but a CASCADE delete on the source row would not be triggered
  through the GFK). The `Notificacion.target` becomes `null` and the bandeja
  shows a stale reference. A periodic cleanup task or a `pre_delete` signal on
  the source models could purge, but neither was needed for the current scope.
