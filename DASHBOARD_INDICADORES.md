# Handoff — Indicadores Dashboard Endpoint

Implementation handoff for the `dashboard/indicadores/` GET endpoint.

- **Branch:** `development`
- **Files created:** `indicadores_dashboard_view.py`, `indicadores_dashboard_urls.py`, `test_indicadores_dashboard.py`
- **Files modified:** `config/urls.py`
- **Domain language:** Spanish (models, fields, messages — keep the convention).

---

## 1. Why this change

The frontend needed a simple dashboard card showing at a glance how many projects a semillero has in active execution and how many have been closed. The existing `DashboardView` aggregates across all semilleros; this endpoint provides per-semillero breakdown with role-based scope control.

---

## 2. API Surface

**Endpoint:** `GET /api/v1/core/dashboard/indicadores/?semillero=<id>`

| Query param | Required | Description |
|-------------|----------|-------------|
| `semillero` | ✅ | ID of the semillero |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "proyectos_activos": 14,
    "proyectos_finalizados": 6
  }
}
```

| Field | Description |
|-------|-------------|
| `proyectos_activos` | Count of proyectos with `estado` in `[EN_EJECUCION, EN_RESULTADOS]` linked to the semillero via M2M |
| `proyectos_finalizados` | Count of proyectos with `estado = CERRADO` linked to the semillero via M2M |

**Error responses:**
- `400` — missing `semillero` or non-integer value
- `403` — user lacks permission to query that semillero

---

## 3. Permission Matrix

| Rol | Access |
|-----|--------|
| `administrador` | Any semillero (no scope restriction) |
| `director_grupo` | Semilleros where `grupo_investigacion.director = user` |
| `director_semillero` | Semilleros where `director = user` |
| `lider_estudiantil` | Forbidden — 403 |
| `estudiante` | Forbidden — 403 |

Scope validation via `_semillero_visible_para(user, semillero_id)` inside `get()`.

---

## 4. Data Model Notes

- `Proyecto` links to `Semillero` via a `ManyToManyField` (`semilleros`).
- **Active states**: `EN_EJECUCION`, `EN_RESULTADOS`
- **Finalized state**: `CERRADO`
- `crecimiento_semilleros` was originally planned but dropped — `Proyecto` has no field linking it to a semester/period, so there is no reliable way to compute period-over-period growth without adding new fields. The response only contains the two project counts.

---

## 5. Files Created / Modified

### View
- `apps/sigesi/views/core/indicadores_dashboard_view.py`
  - `IndicadoresDashboardPermission` — gates by rol (admin/grupo/semillero only)
  - `_semillero_visible_para(user, semillero_id)` — scope validation
  - `IndicadoresDashboardView.get()` — main handler
  - `swagger_fake_view` guard — prevents crashes during drf-yasg schema generation

### Router
- `apps/sigesi/routers/core/indicadores_dashboard_urls.py`
  - Plain `path()` (not DefaultRouter)
  - Registered **before** `dashboard_urls` so `/dashboard/indicadores/` is matched before the existing `/dashboard/` route (which would otherwise shadow it)

### URL wiring
- `config/urls.py` — `indicadores_dashboard_urls` included before `dashboard_urls`

### Tests
- `apps/sigesi/tests/test_indicadores_dashboard.py`
  - 9 test cases: admin happy-path, missing/invalid semillero → 400, director_grupo (own + 403 on unrelated), director_semillero (own + 403 on others), estudiante/lider → 403

---

## 6. How to Verify

```powershell
# Check for import errors
.\.venv\Scripts\python.exe manage.py check

# Run tests
.\.venv\Scripts\python.exe -m pytest apps\sigesi\tests\test_indicadores_dashboard.py --tb=short
```

Manual via Swagger:
1. Login as admin → `GET /api/v1/core/dashboard/indicadores/?semillero=<id>`
2. Verify response: `success: true`, `data` contains `{proyectos_activos, proyectos_finalizados}`
3. Login as estudiante → same request → expect 403
4. Login as director_grupo on a semillero you own → 200; on a semillero you don't → 403

---

## 7. Open Decisions / Follow-ups

- **`crecimiento_semilleros`**: if you later add a `semestre` field to `Proyecto` (or link it to `PlanAccion` via a FK), the growth percentage can be re-added using the `_get_periodos()` helper already drafted in the earlier plan.
- **No `periodo` filter**: currently all proyectos linked to the semillero are counted regardless of date. If you need to scope by semester, a `semestre` field on `Proyecto` would be needed.
- **Null `linea_investigacion`**: not applicable here since this endpoint only counts, it doesn't group by line (that's the `produccion-academica/dashboard/` endpoint).