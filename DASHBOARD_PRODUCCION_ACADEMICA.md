# Handoff — ProduccionAcademica Dashboard Endpoint

Implementation handoff for the `produccion-academica/dashboard/` endpoint.

- **Branch:** `development`
- **Files created:** `produccion_academica_dashboard_view.py`, `produccion_academica_dashboard_urls.py`, `test_produccion_academica_dashboard.py`
- **Files modified:** `config/urls.py`
- **Domain language:** Spanish (models, fields, messages — keep the convention).

---

## 1. Why this change

The frontend需要一个仪表盘，显示每个研究线条的学术产出统计：去重作者数（参与度）和产出数量。现有的 API 没有提供这个聚合视图，所以创建了一个专门的 endpoints。

---

## 2. API Surface

**Endpoint:** `POST /api/v1/core/produccion-academica/dashboard/`

**Request body:**
```json
{
  "periodo": "2026-1",
  "semillero_id": 2,
  "cohorte": "2024"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `semillero_id` | integer | ✅ | ID of the semillero to query |
| `periodo` | string | ❌ | Semester in `'YYYY-1'` or `'YYYY-2'` format. Filters productions by `fecha_publicacion` |
| `cohorte` | string | ❌ | Year prefix (e.g. `'2024'`). Filters autores who have an active `MatriculaSemillero` entry where `semestre` starts with this value |

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "linea_investigacion": "Ingeniería de Software",
      "participacion": 82,
      "produccion_academica": 31
    },
    {
      "linea_investigacion": "Inteligencia Artificial",
      "participacion": 33,
      "produccion_academica": 14
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `linea_investigacion` | Name of the research line |
| `participacion` | Count of **distinct** autores (no duplicates) |
| `produccion_academica` | Total count of `ProduccionAcademica` records |

**Error responses:**
- `400` — missing `semillero_id` or invalid `periodo` format
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

Scope validation is performed by `_semillero_visible_para(user, semillero_id)` before any query runs.

---

## 4. Data Model Mapping

| Param | Model field | Logic |
|-------|-------------|-------|
| `semillero_id` | `ProduccionAcademica.semillero_id` | Direct filter |
| `periodo` | `ProduccionAcademica.fecha_publicacion` | `'YYYY-1'` → Jan–Jun of year; `'YYYY-2'` → Jul–Dec of year |
| `cohorte` | `MatriculaSemillero.semestre` + `User` M2M through `autores` | Only autores with an **active** `MatriculaSemillero` entry whose `semestre` **starts with** `cohorte` (e.g. `'2024'` matches `'2024-1'` and `'2024-2'`) |

`linea_investigacion` can be `NULL` on `ProduccionAcademica`. Null lines appear under `"Sin línea asignada"` in the response.

---

## 5. Files Created / Modified

### View
- `apps/sigesi/views/core/produccion_academica_dashboard_view.py`
  - `ProduccionAcademicaDashboardPermission` — gates by rol (admin/grupo/semillero only)
  - `_parse_periodo(periodo)` — converts `'YYYY-1'`/`'YYYY-2'` → `(year, [months])` or `(None, None)`
  - `_semillero_visible_para(user, semillero_id)` — scope validation
  - `ProduccionAcademicaDashboardView.post()` — main handler
  - `swagger_fake_view` guard — prevents crashes during drf-yasg schema generation

### Router
- `apps/sigesi/routers/core/produccion_academica_dashboard_urls.py`
  - Plain `path()` (not DefaultRouter), registered under `api/v1/core/`

### URL wiring
- `config/urls.py` — included **before** `producciones_academicas_urls` to avoid route shadowing

### Tests
- `apps/sigesi/tests/test_produccion_academica_dashboard.py`
  - 10 test cases: admin happy-path, director_grupo (own + unrelated semillero), director_semillero (own + others' semillero), estudiante/lider 403, missing semillero_id 400, invalid periodo 400, response shape verification

---

## 6. Query Architecture

```python
# Base queryset — productions for the given semillero
producciones_qs = ProduccionAcademica.objects.filter(semillero_id=semillero_id)

# Optional date filter (periodo)
if periodo:
    year, meses = _parse_periodo(periodo)
    producciones_qs = producciones_qs.filter(
        fecha_publicacion__year=year,
        fecha_publicacion__month__in=meses,
    )

# Optional autor filter (cohorte)
if cohorte:
    autores_cohorte = User.objects.filter(
        matriculas_semillero__semestre__startswith=cohorte,
        matriculas_semillero__estado='activa',
        matriculas_semillero__semillero_id=semillero_id,
    )
    producciones_qs = producciones_qs.filter(autores__in=autores_cohorte)

# Aggregation
producciones_qs
    .values(linea_fk=F('linea_investigacion'))
    .annotate(
        linea_nombre=F('linea_investigacion__nombre'),
        participacion=Count('autores', distinct=True),
        produccion_academica=Count('id', distinct=True),
    ).order_by('linea_nombre')
```

---

## 7. How to Verify

```powershell
# Check for import errors
.\.venv\Scripts\python.exe manage.py check

# Run tests
.\.venv\Scripts\python.exe -m pytest `
  apps\sigesi\tests\test_produccion_academica_dashboard.py --tb=short
```

Manual via Swagger:
1. Login as admin → `POST /api/v1/core/produccion-academica/dashboard/` with `{"semillero_id": 2, "periodo": "2026-1", "cohorte": "2024"}`
2. Verify response: `success: true`, `data` is an array of `{linea_investigacion, participacion, produccion_academica}`
3. Login as estudiante → same request → expect 403

---

## 8. Open Decisions / Follow-ups

- **Null linea_investigacion**: productions without a line appear under `"Sin línea asignada"`. If you want to exclude them instead, add `.filter(linea_investigacion__isnull=False)` before the `.values()` call.
- **Empty data handling**: when no productions match, the response returns `[]` in `data` with `success: true`. This is intentional — the frontend can handle an empty array the same as a populated one.
- **No paginated output**: this endpoint is not a ViewSet; it returns a flat array directly. If you need pagination later, convert to `APIView` with manual pagination or a ViewSet with a custom action.