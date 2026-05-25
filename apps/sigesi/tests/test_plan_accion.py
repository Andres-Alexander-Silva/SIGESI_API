"""Smoke tests for /api/v1/core/plan-accion/ — CRUD, scope, aval gate, aprobar."""
from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.sigesi.models import (
    ActividadCronograma,
    Cronograma,
    MatriculaSemillero,
    ObjetivosPlanAccion,
    PlanAccion,
)


URL = '/api/v1/core/plan-accion/'


def _payload(semillero, semestre='2025-1', **overrides):
    data = {
        'semillero': semillero.id,
        'titulo': 'Plan semestral',
        'semestre': semestre,
        'objetivos': [
            {'descripcion': 'Objetivo uno', 'categoria': 'academicos'},
        ],
        'metas': 'Metas del plan.',
    }
    data.update(overrides)
    return data


def _make_plan(semillero, semestre='2025-1', **overrides):
    return PlanAccion.objects.create(
        semillero=semillero,
        titulo='Plan',
        semestre=semestre,
        metas='m',
        **overrides,
    )


# --------------------------------------------------------------------------- #
# Happy paths per allowed role
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_admin_can_create_plan(auth_client, admin_user, semillero_aprobado):
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_director_grupo_can_create_plan(auth_client, director_grupo, semillero_aprobado):
    client = auth_client(director_grupo)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_director_semillero_can_create_plan(auth_client, director_semillero, semillero_aprobado):
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 201, resp.content


# --------------------------------------------------------------------------- #
# Estudiante is read-only
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_estudiante_cannot_create_plan(auth_client, estudiante, semillero_aprobado):
    client = auth_client(estudiante)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_estudiante_can_list_plans_of_own_semillero(
    auth_client, estudiante, semillero_aprobado
):
    _make_plan(semillero_aprobado)
    MatriculaSemillero.objects.create(estudiante=estudiante, semillero=semillero_aprobado, semestre='2025-1')

    client = auth_client(estudiante)
    resp = client.get(URL)
    assert resp.status_code == 200, resp.content
    assert resp.json()['count'] == 1


# --------------------------------------------------------------------------- #
# Aval gate
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_create_plan_when_semillero_not_aprobado_returns_400(
    auth_client, director_semillero, semillero_sin_aprobar
):
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(semillero_sin_aprobar), format='json')
    assert resp.status_code == 400, resp.content


# --------------------------------------------------------------------------- #
# unique_together (semillero, semestre)
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_duplicate_semillero_semestre_returns_400(
    auth_client, admin_user, semillero_aprobado
):
    _make_plan(semillero_aprobado, semestre='2025-1')
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(semillero_aprobado, semestre='2025-1'), format='json')
    assert resp.status_code == 400, resp.content


# --------------------------------------------------------------------------- #
# Filters
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_filter_by_semillero_and_semestre(
    auth_client, admin_user, semillero_aprobado, semillero_sin_aprobar
):
    _make_plan(semillero_aprobado, semestre='2025-1')
    _make_plan(semillero_aprobado, semestre='2025-2')
    _make_plan(semillero_sin_aprobar, semestre='2025-1')

    client = auth_client(admin_user)

    resp = client.get(f'{URL}?semillero={semillero_aprobado.id}')
    assert resp.status_code == 200
    assert resp.json()['count'] == 2

    resp = client.get(f'{URL}?semillero={semillero_aprobado.id}&semestre=2025-2')
    assert resp.status_code == 200
    assert resp.json()['count'] == 1


# --------------------------------------------------------------------------- #
# Row-level scope
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_director_semillero_does_not_see_other_semillero_plans(
    auth_client, director_semillero, semillero_aprobado, grupo, lider_estudiantil
):
    from apps.sigesi.models import Semillero, User

    otro_director = User.objects.create(
        username='otrodir', cedula='CCOTRO1', roles=['director_semillero'],
        correo_personal='otrodir@example.com', email='otrodir@inst.edu',
    )
    otro_semillero = Semillero.objects.create(
        nombre='Otro', codigo='SOTRO', objetivo='o',
        fecha_creacion=semillero_aprobado.fecha_creacion,
        grupo_investigacion=grupo, director=otro_director,
        estado_aval=Semillero.EstadoAvalChoices.APROBADO,
    )
    _make_plan(semillero_aprobado)
    _make_plan(otro_semillero)

    client = auth_client(director_semillero)
    resp = client.get(URL)
    assert resp.status_code == 200
    assert resp.json()['count'] == 1


# --------------------------------------------------------------------------- #
# aprobar action
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_admin_can_aprobar_plan(auth_client, admin_user, semillero_aprobado):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(admin_user)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == PlanAccion.EstadoChoices.APROBADO
    assert plan.aprobado_por == admin_user
    assert plan.fecha_aprobacion is not None


@pytest.mark.django_db
def test_director_grupo_can_aprobar_plan_of_own_group(
    auth_client, director_grupo, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_grupo)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == PlanAccion.EstadoChoices.APROBADO
    assert plan.aprobado_por == director_grupo


@pytest.mark.django_db
def test_aprobar_already_aprobado_returns_400(auth_client, admin_user, semillero_aprobado):
    plan = _make_plan(semillero_aprobado, estado=PlanAccion.EstadoChoices.APROBADO)
    client = auth_client(admin_user)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_director_semillero_cannot_aprobar_plan(
    auth_client, director_semillero, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_semillero)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_aprobar_plan(
    auth_client, estudiante, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(estudiante)
    resp = client.post(f'{URL}{plan.id}/aprobar/')
    assert resp.status_code == 403, resp.content


# --------------------------------------------------------------------------- #
# rechazar action
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_admin_can_rechazar_plan(auth_client, admin_user, semillero_aprobado):
    plan = _make_plan(
        semillero_aprobado,
        estado=PlanAccion.EstadoChoices.APROBADO,
        aprobado_por=admin_user,
        fecha_aprobacion=timezone.now(),
    )
    client = auth_client(admin_user)
    resp = client.post(f'{URL}{plan.id}/rechazar/')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == PlanAccion.EstadoChoices.RECHAZADO
    assert plan.aprobado_por is None
    assert plan.fecha_aprobacion is None


@pytest.mark.django_db
def test_director_grupo_can_rechazar_plan_of_own_group(
    auth_client, director_grupo, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_grupo)
    resp = client.post(f'{URL}{plan.id}/rechazar/')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == PlanAccion.EstadoChoices.RECHAZADO


@pytest.mark.django_db
def test_rechazar_already_rechazado_returns_400(auth_client, admin_user, semillero_aprobado):
    plan = _make_plan(semillero_aprobado, estado=PlanAccion.EstadoChoices.RECHAZADO)
    client = auth_client(admin_user)
    resp = client.post(f'{URL}{plan.id}/rechazar/')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_director_semillero_cannot_rechazar_plan(
    auth_client, director_semillero, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_semillero)
    resp = client.post(f'{URL}{plan.id}/rechazar/')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_rechazar_plan(
    auth_client, estudiante, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(estudiante)
    resp = client.post(f'{URL}{plan.id}/rechazar/')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_lider_cannot_rechazar_plan(
    auth_client, lider_estudiantil, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(lider_estudiantil)
    resp = client.post(f'{URL}{plan.id}/rechazar/')
    assert resp.status_code == 403, resp.content


# --------------------------------------------------------------------------- #
# estado transitions via PUT/PATCH
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_patch_estado_aprobado_stamps_like_aprobar(
    auth_client, director_grupo, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_grupo)
    resp = client.patch(f'{URL}{plan.id}/', {'estado': 'aprobado'}, format='json')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == PlanAccion.EstadoChoices.APROBADO
    assert plan.aprobado_por == director_grupo
    assert plan.fecha_aprobacion is not None


@pytest.mark.django_db
def test_admin_patch_estado_aprobado_stamps(auth_client, admin_user, semillero_aprobado):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(admin_user)
    resp = client.patch(f'{URL}{plan.id}/', {'estado': 'aprobado'}, format='json')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.aprobado_por == admin_user
    assert plan.fecha_aprobacion is not None


@pytest.mark.django_db
def test_director_semillero_cannot_set_estado_aprobado_via_patch(
    auth_client, director_semillero, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_semillero)
    resp = client.patch(f'{URL}{plan.id}/', {'estado': 'aprobado'}, format='json')
    assert resp.status_code == 403, resp.content

    plan.refresh_from_db()
    assert plan.aprobado_por is None


@pytest.mark.django_db
@pytest.mark.parametrize('estado', ['borrador', 'enviado', 'rechazado'])
def test_patch_estado_borrador_or_enviado_clears_aprobacion(
    auth_client, admin_user, semillero_aprobado, estado
):
    plan = _make_plan(
        semillero_aprobado,
        estado=PlanAccion.EstadoChoices.APROBADO,
        aprobado_por=admin_user,
    )
    client = auth_client(admin_user)
    resp = client.patch(f'{URL}{plan.id}/', {'estado': estado}, format='json')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == estado
    assert plan.aprobado_por is None
    assert plan.fecha_aprobacion is None


@pytest.mark.django_db
def test_patch_rechazado_without_prior_approval_clears_aprobacion(
    auth_client, admin_user, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)  # never approved
    client = auth_client(admin_user)
    resp = client.patch(f'{URL}{plan.id}/', {'estado': 'rechazado'}, format='json')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == PlanAccion.EstadoChoices.RECHAZADO
    assert plan.aprobado_por is None
    assert plan.fecha_aprobacion is None


@pytest.mark.django_db
@pytest.mark.parametrize('estado', ['en_ejecucion', 'finalizado'])
def test_patch_other_estado_requires_prior_approval(
    auth_client, admin_user, semillero_aprobado, estado
):
    plan = _make_plan(semillero_aprobado)  # never approved
    client = auth_client(admin_user)
    resp = client.patch(f'{URL}{plan.id}/', {'estado': estado}, format='json')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
@pytest.mark.parametrize('estado', ['en_ejecucion', 'finalizado'])
def test_patch_other_estado_allowed_when_previously_approved(
    auth_client, admin_user, semillero_aprobado, estado
):
    fecha = timezone.now()
    plan = _make_plan(
        semillero_aprobado,
        estado=PlanAccion.EstadoChoices.APROBADO,
        aprobado_por=admin_user,
        fecha_aprobacion=fecha,
    )
    client = auth_client(admin_user)
    resp = client.patch(f'{URL}{plan.id}/', {'estado': estado}, format='json')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.estado == estado
    # El sello de aprobación se conserva.
    assert plan.aprobado_por == admin_user
    assert plan.fecha_aprobacion == fecha


@pytest.mark.django_db
def test_put_resending_aprobado_on_approved_plan_is_noop(
    auth_client, admin_user, semillero_aprobado
):
    fecha = timezone.now()
    plan = _make_plan(
        semillero_aprobado,
        estado=PlanAccion.EstadoChoices.APROBADO,
        aprobado_por=admin_user,
        fecha_aprobacion=fecha,
    )
    client = auth_client(admin_user)
    resp = client.put(f'{URL}{plan.id}/', {
        'semillero': semillero_aprobado.id,
        'titulo': 'Plan editado',
        'semestre': '2025-1',
        'objetivos': [{'descripcion': 'o2', 'categoria': 'investigativos'}],
        'metas': 'm2',
        'estado': 'aprobado',
    }, format='json')
    assert resp.status_code == 200, resp.content

    plan.refresh_from_db()
    assert plan.titulo == 'Plan editado'
    assert plan.aprobado_por == admin_user
    assert plan.fecha_aprobacion == fecha  # no re-sello


# --------------------------------------------------------------------------- #
# objetivos anidados (ObjetivosPlanAccion)
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_create_plan_with_objetivos(auth_client, admin_user, semillero_aprobado):
    client = auth_client(admin_user)
    payload = _payload(semillero_aprobado, objetivos=[
        {'descripcion': 'Objetivo académico', 'categoria': 'academicos'},
        {'descripcion': 'Objetivo investigativo', 'categoria': 'investigativos'},
    ])
    resp = client.post(URL, payload, format='json')
    assert resp.status_code == 201, resp.content

    objetivos = resp.data['data']['objetivos']
    assert len(objetivos) == 2
    assert {o['categoria'] for o in objetivos} == {'academicos', 'investigativos'}


@pytest.mark.django_db
def test_invalid_categoria_returns_400(auth_client, admin_user, semillero_aprobado):
    client = auth_client(admin_user)
    payload = _payload(semillero_aprobado, objetivos=[
        {'descripcion': 'X', 'categoria': 'inexistente'},
    ])
    resp = client.post(URL, payload, format='json')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_update_replaces_objetivos(auth_client, admin_user, semillero_aprobado):
    from apps.sigesi.models import ObjetivosPlanAccion

    plan = _make_plan(semillero_aprobado)
    ObjetivosPlanAccion.objects.create(
        plan_accion=plan, descripcion='Viejo', categoria='academicos')

    client = auth_client(admin_user)
    resp = client.patch(
        f'{URL}{plan.id}/',
        {'objetivos': [
            {'descripcion': 'Nuevo A', 'categoria': 'administrativos'},
            {'descripcion': 'Nuevo B', 'categoria': 'institucionales'},
        ]},
        format='json',
    )
    assert resp.status_code == 200, resp.content

    descripciones = set(plan.objetivos.values_list('descripcion', flat=True))
    assert descripciones == {'Nuevo A', 'Nuevo B'}  # los previos se reemplazan


@pytest.mark.django_db
def test_retrieve_embeds_objetivos(auth_client, admin_user, semillero_aprobado):
    from apps.sigesi.models import ObjetivosPlanAccion

    plan = _make_plan(semillero_aprobado)
    ObjetivosPlanAccion.objects.create(
        plan_accion=plan, descripcion='Obj', categoria='investigativos')

    client = auth_client(admin_user)
    resp = client.get(f'{URL}{plan.id}/')
    assert resp.status_code == 200, resp.content
    assert isinstance(resp.data['objetivos'], list)
    assert resp.data['objetivos'][0]['descripcion'] == 'Obj'
    assert resp.data['objetivos'][0]['categoria'] == 'investigativos'


# --------------------------------------------------------------------------- #
# dashboard action
# --------------------------------------------------------------------------- #

def _seed_dashboard(plan, responsable):
    """Crea 3 objetivos (2 académicos, 1 investigativo) y 4 actividades.

    Actividades: 2 completadas (una a tiempo, una atrasada) y 2 pendientes
    (una atrasada por vencimiento, una a tiempo). Todas con ``responsable``.
    """
    hoy = date.today()
    ObjetivosPlanAccion.objects.create(plan_accion=plan, descripcion='a1', categoria='academicos')
    ObjetivosPlanAccion.objects.create(plan_accion=plan, descripcion='a2', categoria='academicos')
    ObjetivosPlanAccion.objects.create(plan_accion=plan, descripcion='i1', categoria='investigativos')

    cron = Cronograma.objects.create(
        plan_accion=plan, responsable=responsable, fecha_inicio=hoy, fecha_fin=hoy)
    comp = ActividadCronograma.EstadoChoices.COMPLETADA
    pend = ActividadCronograma.EstadoChoices.PENDIENTE
    # completada a tiempo
    ActividadCronograma.objects.create(
        cronograma=cron, titulo='c-ok', responsable=responsable, estado=comp,
        fecha_inicio=hoy - timedelta(days=10),
        fecha_fin_estimada=hoy, fecha_fin=hoy - timedelta(days=1))
    # completada atrasada (fecha_fin > estimada)
    ActividadCronograma.objects.create(
        cronograma=cron, titulo='c-late', responsable=responsable, estado=comp,
        fecha_inicio=hoy - timedelta(days=10),
        fecha_fin_estimada=hoy - timedelta(days=5), fecha_fin=hoy)
    # pendiente atrasada (estimada ya pasó)
    ActividadCronograma.objects.create(
        cronograma=cron, titulo='p-late', responsable=responsable, estado=pend,
        fecha_inicio=hoy - timedelta(days=10),
        fecha_fin_estimada=hoy - timedelta(days=1))
    # pendiente a tiempo (estimada en el futuro)
    ActividadCronograma.objects.create(
        cronograma=cron, titulo='p-ok', responsable=responsable, estado=pend,
        fecha_inicio=hoy,
        fecha_fin_estimada=hoy + timedelta(days=10))


@pytest.mark.django_db
def test_admin_dashboard_metrics(auth_client, admin_user, semillero_aprobado, director_semillero):
    plan = _make_plan(semillero_aprobado)
    _seed_dashboard(plan, director_semillero)

    client = auth_client(admin_user)
    resp = client.get(f'{URL}{plan.id}/dashboard/')
    assert resp.status_code == 200, resp.content
    data = resp.json()

    # Distribución de objetivos por categoría: 2/3 académicos, 1/3 investigativos.
    cats = {c['categoria']: c for c in data['objetivos_por_categoria']['categorias']}
    assert data['objetivos_por_categoria']['total'] == 3
    assert len(cats) == 4  # las 4 categorías siempre presentes
    assert cats['academicos']['cantidad'] == 2
    assert cats['academicos']['porcentaje'] == 66.67
    assert cats['investigativos']['porcentaje'] == 33.33
    assert cats['administrativos']['porcentaje'] == 0.0

    # Cumplimiento: 2 de 4 completadas.
    assert data['cumplimiento_actividades'] == {'total': 4, 'completadas': 2, 'porcentaje': 50.0}

    # Puntualidad: 2 atrasadas (c-late, p-late), 2 a tiempo.
    assert data['puntualidad'] == {'total': 4, 'a_tiempo': 2, 'atrasadas': 2}

    # Por responsable: el director de semillero tiene 4 asignadas, 2 completadas.
    por_resp = data['actividades_por_responsable']
    assert len(por_resp) == 1
    assert por_resp[0]['responsable_id'] == director_semillero.id
    assert por_resp[0]['asignadas'] == 4
    assert por_resp[0]['completadas'] == 2
    assert por_resp[0]['porcentaje'] == 50.0


@pytest.mark.django_db
def test_director_semillero_can_see_own_plan_dashboard(
    auth_client, director_semillero, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(director_semillero)
    resp = client.get(f'{URL}{plan.id}/dashboard/')
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
def test_estudiante_can_see_dashboard_of_own_semillero(
    auth_client, estudiante, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)
    MatriculaSemillero.objects.create(
        estudiante=estudiante, semillero=semillero_aprobado, semestre='2025-1')
    client = auth_client(estudiante)
    resp = client.get(f'{URL}{plan.id}/dashboard/')
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_see_dashboard_of_other_semillero(
    auth_client, estudiante, semillero_aprobado
):
    plan = _make_plan(semillero_aprobado)  # estudiante NO matriculado
    client = auth_client(estudiante)
    resp = client.get(f'{URL}{plan.id}/dashboard/')
    assert resp.status_code == 404, resp.content


@pytest.mark.django_db
def test_dashboard_empty_plan_returns_zeros(auth_client, admin_user, semillero_aprobado):
    plan = _make_plan(semillero_aprobado)
    client = auth_client(admin_user)
    resp = client.get(f'{URL}{plan.id}/dashboard/')
    assert resp.status_code == 200, resp.content
    data = resp.json()

    assert data['objetivos_por_categoria']['total'] == 0
    assert all(c['porcentaje'] == 0.0 for c in data['objetivos_por_categoria']['categorias'])
    assert data['cumplimiento_actividades'] == {'total': 0, 'completadas': 0, 'porcentaje': 0.0}
    assert data['puntualidad'] == {'total': 0, 'a_tiempo': 0, 'atrasadas': 0}
    assert data['actividades_por_responsable'] == []
