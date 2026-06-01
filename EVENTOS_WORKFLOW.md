# Handoff — Eventos Workflow (Evento → Convocatoria → Postulación → Participación)

Implementation handoff for the four-model academic-events workflow.

- **Branch:** `development`
- **Migrations introduced:** `0025_workflow_convocatoria_postulacion` (data wipe) + `0026_workflow_fks` (schema)
- **Domain language:** Spanish (models, fields, messages — keep the convention).

---

## 1. Why this change

`Evento` and `ParticipacionEvento` already had full API stacks, but `Convocatoria`
and `Postulacion` existed as **model-only stubs** (no serializers/views/routers/
permissions) and the four models were **not connected**:

- `Convocatoria` had **no FK to `Evento`**.
- `ParticipacionEvento` had **no link to `Postulacion`/`Convocatoria`**.

Goal: wire a single linear workflow with the right role gate at each step, row-level
scope filters, the Semillero aval gate, and validations that enforce step ordering.

---

## 2. The workflow

```
[administrador]                 [admin | director_grupo]
   Evento  ───────────────────►  Convocatoria (FK→Evento, requerido)
                                       │
                                       ▼
                              [director_semillero]
                               Postulacion (FK→Convocatoria, FK→Semillero, M2M estudiantes)
                                       │  estado: pendiente → aceptada/rechazada
                                       │  (aprobar/rechazar: admin | director_grupo)
                                       ▼
                       [admin | director_semillero | lider_estudiantil]
                        ParticipacionEvento (FK→Evento, +FK→Postulacion)
                        gate: el participante debe estar en una Postulación ACEPTADA
```

### Permission matrix (the "rules")

| Step | Resource | Write (create/update/delete) | Read | Special action |
|------|----------|------------------------------|------|----------------|
| 1 | `Evento` | **administrador** | all authenticated | — |
| 2 | `Convocatoria` | **administrador, director_grupo** | all authenticated | — |
| 3 | `Postulacion` | **administrador, director_semillero** (own semillero only) | role-scoped rows | `aprobar`/`rechazar` → **admin + director_grupo** |
| 4 | `ParticipacionEvento` | **administrador, director_semillero, lider_estudiantil** | `participantes_en_alcance` scope | `cargar-certificado` (existing) |

**`Postulacion` row-scope (`get_queryset`)** — admin → all; director_grupo →
`semillero__grupo_investigacion__director=user`; director_semillero →
`semillero__director=user`; lider_estudiantil → `semillero__lider_estudiantil=user`;
estudiante → `estudiantes=user` (read-only).

---

## 3. Business rules & where they live

- **Aval gate** — `Postulacion` is tied to a `Semillero`, so a non-admin cannot
  postulate a semillero whose `estado_aval != aprobado`. Enforced via
  `validar_semilleros_avalados([semillero], user, field_name='semillero')`
  ([utils/aval.py](apps/sigesi/utils/aval.py)) in `PostulacionCreateUpdateSerializer.validate()`.
- **Own-semillero** — non-admin director_semillero may only postulate a semillero
  they direct (serializer `validate()`).
- **Matrícula** — every user in `estudiantes` must be matriculated in that semillero
  (`semillero.matriculas`) and hold estudiante/líder role (serializer `validate()`).
- **Convocatoria abierta** — on create, `convocatoria.estado` must be `abierta`
  (serializer `validate()`).
- **Workflow gate (the load-bearing rule)** — registering a `ParticipacionEvento`
  requires, for non-admin, an **`aceptada`** `Postulacion` whose
  `convocatoria.evento == evento` and whose `estudiantes` contains the `participante`.
  If a `postulacion` FK is supplied explicitly, it must match the event, be accepted,
  and contain the participante. Enforced in
  `ParticipacionEventoCreateUpdateSerializer.validate()`
  ([participacion_evento_serializer.py](apps/sigesi/serializers/core/participacion_evento_serializer.py)).
- **Resolution gate** — `aprobar`/`rechazar` re-check the admin/director_grupo role
  **inside** the action (the `*RolePermission` alone lets director_semillero through),
  then stamp `estado`/`aprobado_por`/`fecha_resolucion`. Mirrors the
  `PlanEstrategico` approval actions.

---

## 4. Files changed / created

### Models & migration
- `apps/sigesi/models.py` — `Convocatoria.evento` (required FK), `Postulacion.aprobado_por`
  + `Postulacion.fecha_resolucion`, `ParticipacionEvento.postulacion` (nullable FK).
- `apps/sigesi/migrations/0025_workflow_convocatoria_postulacion.py` — **wipes
  pre-existing convocatorias** (data-only `RunPython`, cascades to their postulaciones),
  mirroring the wipe pattern in `0024`.
- `apps/sigesi/migrations/0026_workflow_fks.py` — adds the non-null `Convocatoria.evento`
  FK plus the new `Postulacion`/`ParticipacionEvento` fields.
  - **Why two migrations:** Postgres raises `ObjectInUse` ("pending trigger events") if a
    cascading `DELETE` (ORM) and an `ALTER TABLE` on the same table run in one transaction.
    A Django migration is atomic, so the wipe (0025) must commit before the `AddField`
    (0026) runs. Don't merge them back into one.

### Permissions
- `apps/sigesi/decorators/permissions.py` — added `ConvocatoriaRolePermission` and
  `PostulacionRolePermission` (the latter uses `view.action` to split create/update
  from the resolution actions).

### New API stacks (mirror existing layer structure)
- `serializers/core/convocatoria_serializer.py`, `serializers/core/postulacion_serializer.py`
- `views/core/convocatoria_view.py`, `views/core/postulacion_view.py`
- `routers/core/convocatorias_urls.py`, `routers/core/postulaciones_urls.py`

### Wiring & ancillary
- `config/urls.py` — registered `convocatorias_urls` + `postulaciones_urls`.
- `serializers/core/participacion_evento_serializer.py` — added `postulacion` field +
  the workflow gate in `validate()`.
- `apps/sigesi/management/commands/seed_mock_data.py` — convocatorias moved from
  `_seed_catalogos` (phase 1) to `_seed_convocatorias_indicadores_informes` (phase 9),
  so an `Evento` exists to attach.

### Docs
- `CLAUDE.md` — replaced the "Eventos & participaciones" bullet with the full
  four-step workflow description; added the two new permission classes to the RBAC list.

### Tests
- `apps/sigesi/tests/test_convocatoria.py` (new) — RBAC write/read, required `evento`,
  date-range validation.
- `apps/sigesi/tests/test_postulacion.py` (new) — own-semillero, aval gate, matrícula,
  convocatoria-abierta, `aprobar`/`rechazar` role gate, row-scope filter.
- `apps/sigesi/tests/test_participacion_evento.py` (updated) — the existing non-admin
  happy-path tests now set up an accepted `Postulacion` (the gate changed their
  behavior); added explicit gate tests (blocked without accepted postulación, blocked
  when pending, admin bypass).

---

## 5. API surface

Base: `/api/v1/core/`

- `GET/POST /convocatorias/`, `GET/PUT/PATCH/DELETE /convocatorias/{id}/` — filters `?evento=&estado=&tipo=`
- `GET/POST /postulaciones/`, `GET/PUT/PATCH/DELETE /postulaciones/{id}/` — filters `?convocatoria=&semillero=&estado=`
  - `POST /postulaciones/{id}/aprobar/` — accepts optional `resultado`/`observaciones`
  - `POST /postulaciones/{id}/rechazar/` — accepts optional `resultado`/`observaciones`
- `GET/POST /participaciones-evento/` … `POST /participaciones-evento/{id}/cargar-certificado/` (unchanged)

---

## 6. How to run / verify

```powershell
# Apply the migration (run manage.py through the venv — system Python lacks celery)
.\.venv\Scripts\python.exe manage.py migrate

# Tests (first run after the migration needs --create-db)
.\.venv\Scripts\python.exe -m pytest `
  apps/sigesi/tests/test_convocatoria.py `
  apps/sigesi/tests/test_postulacion.py `
  apps/sigesi/tests/test_participacion_evento.py --create-db
```

Manual happy-path via `/swagger/`:
1. admin `POST /eventos/`
2. admin/director_grupo `POST /convocatorias/` (with `evento`)
3. director_semillero `POST /postulaciones/`
4. director_grupo `POST /postulaciones/{id}/aprobar/`
5. director_semillero/lider `POST /participaciones-evento/` — succeeds **only** after
   the postulación is accepted.

Validated so far: `manage.py check` passes; the 36 tests in the three files **collect**
cleanly. Per repo policy the suite was **not executed** automatically — run the command
above.

---

## 7. Open decisions / follow-ups

- **`aprobado_por` on reject.** Current behavior stamps `aprobado_por` on *both*
  `aprobar` and `rechazar` (read it as "resolved by", for audit). `PlanEstrategico.rechazar`
  instead *clears* it. If you want reject to clear it, change `_resolver` in
  [postulacion_view.py](apps/sigesi/views/core/postulacion_view.py) (one line).
- **No RBAC `Menu/Opcion/Permiso` rows** were added — these viewsets gate via
  `*RolePermission` classes, not the stale data-driven `Permiso` lookup. Add menu
  entries only if the frontend's data-driven menu needs them.
- **`ParticipacionEvento.postulacion` is optional.** Admin can still register
  participations without a postulación (gate bypass). If every participation must be
  tied to a postulación, make the FK required and drop the admin bypass in the
  serializer.
- **`Convocatoria` is event-scoped now** (required FK). The model's original
  "internal/external standalone call" generality was dropped per the workflow decision.
