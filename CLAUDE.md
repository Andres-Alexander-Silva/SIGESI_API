# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SIGESI API — Django REST Framework backend for the *Plataforma Estratégica de Gestión y Fortalecimiento de Semilleros de Investigación* (research-seedbed management system). Spanish-language domain (models, fields, messages, comments are all in Spanish — keep that convention).

Stack: Django 6 + DRF, PostgreSQL, SimpleJWT, Django Channels + Redis (websockets), Daphne (ASGI), SMTP via `django.core.mail` (email), drf-yasg (Swagger). Configured for deployment on Render.

## Common commands

```powershell
# Dev server (HTTP only)
python manage.py runserver

# Dev server with websockets (Channels/Daphne — required for /ws/permisos/)
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# DB
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Static (production)
python manage.py collectstatic --noinput

# Shell
python manage.py shell
```

There is no test suite, lint config, or pre-commit setup in the repo. `build.sh` is the Render build hook (pip install + collectstatic).

Environment is read via `python-decouple` from a `.env` file at the repo root. Required: `SECRET_KEY`, `DB_*`. Optional: `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `REDIS_HOST`/`REDIS_PORT` (local) or `REDIS_URL` (Render, with `RENDER=true`), `EMAIL_HOST`/`EMAIL_PORT`/`EMAIL_USE_TLS`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`/`DEFAULT_FROM_EMAIL`, `FRONTEND_URL`. Redis is required for the websocket layer — if it's down, `/ws/permisos/` connections fail.

API base: `/api/v1/`. Docs: `/swagger/`, `/redoc/`. Admin: `/panel_admin_sigesi_api/`.

## Architecture

Single Django app (`apps.sigesi`) split by **layer**, not by feature. Each layer has `auth/`, `config/`, and `core/` subfolders that mirror each other:

```
apps/sigesi/
  models.py            # ALL domain models live here (~1345 lines, single file by design)
  consumers.py         # Channels consumer for /ws/permisos/<user_id>/
  middleware/          # Custom JWTAuthentication (extends SimpleJWT)
  decorators/          # @access_permission / @access_function — codigo_opcion-based gates
  views/{auth,config,core}/
  serializers/{auth,config,core}/
  routers/{auth,config,core}/   # one *_urls.py per resource; wired in config/urls.py
  filters/              # django-filter FilterSets
  utils/                # email_service, notifications (channel-layer fan-out), throttles, ordering, time
```

When adding a resource, expect to touch four parallel files: `models.py` → `serializers/<area>/<x>_serializer.py` → `views/<area>/<x>_view.py` → `routers/<area>/<x>_urls.py`, then register the router in `config/urls.py`.

### Auth & RBAC — the load-bearing piece

- `AUTH_USER_MODEL = 'sigesi.User'`. The `User` model has an **`ArrayField` of `roles`** (multi-role per user) with choices: `administrador`, `director_grupo`, `director_semillero`, `lider_estudiantil`, `estudiante`. Do not assume single-role; use `user.tiene_rol(...)` / `user.tiene_alguno_de([...])` helpers on the model.
- Permissions are data-driven: `Menu → Opcion → Permiso(rol, opcion, puede_consultar/crear/actualizar/eliminar)`. Permisos are keyed by `(rol, opcion)`. The decorators in `apps/sigesi/decorators/decorator.py` look up `Permiso` by `opcion__codigo` and the user's `roles` array — but note the decorators reference `opcion__codigo`, `opcion__is_active`, and `permitido` fields that **do not exist** on the current `Opcion`/`Permiso` models (real fields are `url`, `estado`, and the four `puede_*` booleans). Treat the decorator file as out-of-date with the schema; when wiring real permission checks, model them on `User.puede_consultar(url_opcion)` in `models.py` instead.
- JWT auth flow: `apps/sigesi/middleware/authentication_middleware.py` is the default `DEFAULT_AUTHENTICATION_CLASSES`. Public paths are hardcoded in its `EXEMPT_PATHS` list (`/swagger/`, `/redoc/`, `/api/v1/auth/login/`, `/api/v1/auth/refresh/`) — add new public endpoints there, not via per-view `permission_classes = [AllowAny]`, or expect the middleware to still attempt auth.

### Realtime permission updates (Channels)

`config/asgi.py` registers a single websocket route: `ws/permisos/<user_id>/?token=<jwt>`. `PermisosConsumer` validates the JWT against the URL `user_id`, joins group `permisos_user_<id>`, and pushes updates whenever `Permiso` rows change. The fan-out helpers live in `apps/sigesi/utils/notifications.py` and are called from `views/config/rbac_view.py`'s `perform_create/update/partial_update/destroy`. If you add new write paths for `Permiso`, call `notificar_cambio_permiso` (or the multi-user variant) so connected clients refresh.

### Domain shape (read `models.py` for the full graph)

`ProgramaAcademico → GrupoInvestigacion → Semillero → (MatriculaSemillero, PlanEstrategico → PlanAccion → Cronograma)`. `Proyecto` cross-cuts: M2M to `Semillero` and to estudiantes, FKs to `LineaInvestigacion`, director, lider. Then phases/milestones (`FaseProyecto`, `HitoEntregable`), evidencias/avances, inscripciones, etc. Egresados (`is_graduated=True`) have their institutional `email` cleared in `User.save()` — keep that invariant if you touch user serializers.

### Deployment notes

`Procfile` uses **Daphne**, not Gunicorn — http and websockets both go through ASGI. In production (`DEBUG=False`) settings.py forces SSL redirect, secure cookies, and HSTS. `RENDER=true` switches `CHANNEL_LAYERS` to read `REDIS_URL` as a single URL string instead of host/port. See `RENDER_SETUP.md` and `WEBSOCKET_PERMISOS.md` for the full Render + Redis setup.
