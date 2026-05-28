"""Smoke tests para /api/v1/core/evaluaciones/ — CRUD, alcance, aval y calificar.

Cubre: creación por rol (admin / director de semillero), regla de evaluador por
tipo (autoevaluación fuerza evaluador=estudiante; heteroevaluación lo exige),
prohibición de fijar puntaje/observaciones al crear, 403 de creación para roles
de solo lectura, lectura por rol permitido, filtro de alcance por rol, aval gate
sobre el semillero (vía competencia), y la acción ``calificar`` restringida al
evaluador asignado.
"""
from datetime import date

import pytest

from apps.sigesi.models import (
    CompetenciaInvestigativa,
    Evaluacion,
    GrupoInvestigacion,
    MatriculaSemillero,
    Semillero,
)


URL = '/api/v1/core/evaluaciones/'


def _make_competencia(semillero, **overrides):
    defaults = dict(
        nombre='Redacción científica',
        descripcion='Capacidad de escribir artículos.',
        nivel=CompetenciaInvestigativa.NivelChoices.BASICO,
        indicadores='Indicadores de logro.',
    )
    defaults.update(overrides)
    return CompetenciaInvestigativa.objects.create(semillero=semillero, **defaults)


def _make_evaluacion(competencia, estudiante, evaluador, **overrides):
    defaults = dict(
        tipo=Evaluacion.TipoChoices.AUTOEVALUACION,
        semestre='2025-1',
    )
    defaults.update(overrides)
    return Evaluacion.objects.create(
        competencia=competencia,
        estudiante=estudiante,
        evaluador=evaluador,
        **defaults,
    )


def _payload(competencia, estudiante, **overrides):
    data = {
        'competencia': competencia.id,
        'estudiante': estudiante.id,
        'tipo': Evaluacion.TipoChoices.AUTOEVALUACION,
        'semestre': '2025-1',
    }
    data.update(overrides)
    return data


def _filas(resp):
    """Devuelve las filas de la respuesta, sea paginada o no."""
    data = resp.data
    return data['results'] if isinstance(data, dict) and 'results' in data else data


@pytest.fixture
def competencia(db, semillero_aprobado):
    return _make_competencia(semillero_aprobado)


@pytest.fixture
def matricula(db, semillero_aprobado, estudiante):
    """Matricula al estudiante en el semillero aprobado (alcance de lectura)."""
    return MatriculaSemillero.objects.create(
        estudiante=estudiante,
        semillero=semillero_aprobado,
        semestre='2025-1',
    )


@pytest.fixture
def semillero_otro_grupo(db, programa):
    """Semillero de un grupo cuyo director NO es el fixture ``director_grupo``."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    n = User.objects.count() + 1
    otro_director = User.objects.create(
        username=f'otro{n}',
        cedula=f'CC9{n:05d}',
        correo_personal=f'otro{n}@example.com',
        email=f'otro{n}@inst.edu',
        first_name=f'Otro{n}',
        last_name='Director',
        roles=['director_grupo', 'director_semillero'],
        is_active=True,
    )
    otro_director.set_password('x')
    otro_director.save()
    grupo = GrupoInvestigacion.objects.create(
        nombre='Grupo Omega',
        codigo='G9',
        fecha_creacion=date.today(),
        programa_academico=programa,
        director=otro_director,
    )
    return Semillero.objects.create(
        nombre='Semillero Delta',
        codigo='S9',
        objetivo='Otro grupo.',
        fecha_creacion=date.today(),
        grupo_investigacion=grupo,
        director=otro_director,
        estado_aval=Semillero.EstadoAvalChoices.APROBADO,
    )


# --------------------------------------------------------------------------- #
# Create: Administrador y Director de Semillero
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_admin_can_create(auth_client, admin_user, competencia, estudiante):
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(competencia, estudiante), format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_director_semillero_can_create(auth_client, director_semillero, competencia, estudiante):
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(competencia, estudiante), format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_director_grupo_cannot_create(auth_client, director_grupo, competencia, estudiante):
    client = auth_client(director_grupo)
    resp = client.post(URL, _payload(competencia, estudiante), format='json')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_lider_cannot_create(auth_client, lider_estudiantil, competencia, estudiante):
    client = auth_client(lider_estudiantil)
    resp = client.post(URL, _payload(competencia, estudiante), format='json')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_create(auth_client, estudiante, competencia):
    client = auth_client(estudiante)
    resp = client.post(URL, _payload(competencia, estudiante), format='json')
    assert resp.status_code == 403, resp.content


# --------------------------------------------------------------------------- #
# Reglas de evaluador por tipo
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_autoevaluacion_sets_evaluador_to_estudiante(auth_client, admin_user, competencia, estudiante):
    client = auth_client(admin_user)
    payload = _payload(competencia, estudiante, tipo=Evaluacion.TipoChoices.AUTOEVALUACION)
    resp = client.post(URL, payload, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.data['data']['evaluador'] == estudiante.id


@pytest.mark.django_db
def test_heteroevaluacion_requires_evaluador(auth_client, admin_user, competencia, estudiante):
    client = auth_client(admin_user)
    payload = _payload(competencia, estudiante, tipo=Evaluacion.TipoChoices.HETEROEVALUACION)
    resp = client.post(URL, payload, format='json')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_heteroevaluacion_with_evaluador(auth_client, admin_user, competencia, estudiante, director_semillero):
    client = auth_client(admin_user)
    payload = _payload(
        competencia, estudiante,
        tipo=Evaluacion.TipoChoices.HETEROEVALUACION,
        evaluador=director_semillero.id,
    )
    resp = client.post(URL, payload, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.data['data']['evaluador'] == director_semillero.id


@pytest.mark.django_db
def test_create_ignores_puntaje_and_observaciones(auth_client, admin_user, competencia, estudiante):
    client = auth_client(admin_user)
    payload = _payload(competencia, estudiante, puntaje='4.5', observaciones='No debería guardarse')
    resp = client.post(URL, payload, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.data['data']['puntaje'] is None
    assert not resp.data['data']['observaciones']


# --------------------------------------------------------------------------- #
# Read: roles permitidos
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
@pytest.mark.parametrize('rol', ['admin_user', 'director_grupo', 'director_semillero',
                                 'lider_estudiantil', 'estudiante'])
def test_roles_can_read(auth_client, request, rol, competencia, estudiante, matricula):
    _make_evaluacion(competencia, estudiante, estudiante)
    user = request.getfixturevalue(rol)
    client = auth_client(user)
    resp = client.get(URL)
    assert resp.status_code == 200, resp.content


# --------------------------------------------------------------------------- #
# Filtro de alcance por rol
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_director_semillero_only_sees_own(auth_client, director_semillero, competencia,
                                          estudiante, semillero_otro_grupo):
    _make_evaluacion(competencia, estudiante, estudiante)
    otra_comp = _make_competencia(semillero_otro_grupo)
    otra_eval = _make_evaluacion(otra_comp, estudiante, estudiante)
    client = auth_client(director_semillero)
    resp = client.get(URL)
    assert resp.status_code == 200
    ids = {row['id'] for row in _filas(resp)}
    assert otra_eval.id not in ids


@pytest.mark.django_db
def test_director_semillero_cannot_update_other_semillero(
    auth_client, director_semillero, semillero_otro_grupo, estudiante
):
    otra_comp = _make_competencia(semillero_otro_grupo)
    otra_eval = _make_evaluacion(otra_comp, estudiante, estudiante)
    client = auth_client(director_semillero)
    resp = client.patch(f'{URL}{otra_eval.id}/', {'semestre': '2025-2'}, format='json')
    # Queda fuera del queryset del director de semillero -> 404.
    assert resp.status_code == 404, resp.content


# --------------------------------------------------------------------------- #
# Aval gate (vía competencia.semillero)
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_director_semillero_create_blocked_by_aval(
    auth_client, director_semillero, semillero_sin_aprobar, estudiante
):
    comp = _make_competencia(semillero_sin_aprobar)
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(comp, estudiante), format='json')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_director_semillero_cannot_create_for_other_semillero(
    auth_client, director_semillero, semillero_otro_grupo, estudiante
):
    comp = _make_competencia(semillero_otro_grupo)
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(comp, estudiante), format='json')
    # No dirige ese semillero -> 403.
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_admin_bypasses_aval_gate(auth_client, admin_user, semillero_sin_aprobar, estudiante):
    comp = _make_competencia(semillero_sin_aprobar)
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(comp, estudiante), format='json')
    assert resp.status_code == 201, resp.content


# --------------------------------------------------------------------------- #
# Delete
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_admin_can_delete(auth_client, admin_user, competencia, estudiante):
    ev = _make_evaluacion(competencia, estudiante, estudiante)
    client = auth_client(admin_user)
    resp = client.delete(f'{URL}{ev.id}/')
    assert resp.status_code == 204, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_delete(auth_client, estudiante, competencia, matricula):
    ev = _make_evaluacion(competencia, estudiante, estudiante)
    client = auth_client(estudiante)
    resp = client.delete(f'{URL}{ev.id}/')
    assert resp.status_code == 403, resp.content


# --------------------------------------------------------------------------- #
# Calificar: solo el evaluador asignado
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_evaluador_can_calificar_post(auth_client, competencia, estudiante, director_semillero):
    ev = _make_evaluacion(
        competencia, estudiante, director_semillero,
        tipo=Evaluacion.TipoChoices.HETEROEVALUACION,
    )
    client = auth_client(director_semillero)
    payload = {
        'puntaje': '4.5',
        'observaciones': 'Buen desempeño.',
        'nivel_alcanzado': Evaluacion.NivelAlcanzadoChoices.AVANZADO,
    }
    resp = client.post(f'{URL}{ev.id}/calificar/', payload, format='json')
    assert resp.status_code == 200, resp.content
    assert resp.data['data']['nivel_alcanzado'] == Evaluacion.NivelAlcanzadoChoices.AVANZADO
    ev.refresh_from_db()
    assert str(ev.puntaje) == '4.50'


@pytest.mark.django_db
def test_estudiante_can_calificar_own_autoevaluacion(auth_client, competencia, estudiante, matricula):
    # En autoevaluación el evaluador es el propio estudiante.
    ev = _make_evaluacion(competencia, estudiante, estudiante)
    client = auth_client(estudiante)
    payload = {
        'puntaje': '3.0',
        'nivel_alcanzado': Evaluacion.NivelAlcanzadoChoices.INTERMEDIO,
    }
    resp = client.post(f'{URL}{ev.id}/calificar/', payload, format='json')
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
def test_non_evaluador_cannot_calificar(auth_client, competencia, estudiante, admin_user):
    # El evaluador es el estudiante; el admin (que no es el evaluador) no puede calificar.
    ev = _make_evaluacion(competencia, estudiante, estudiante)
    client = auth_client(admin_user)
    payload = {'puntaje': '4.0', 'nivel_alcanzado': Evaluacion.NivelAlcanzadoChoices.BASICO}
    resp = client.post(f'{URL}{ev.id}/calificar/', payload, format='json')
    assert resp.status_code in (403, 404), resp.content


@pytest.mark.django_db
def test_calificar_puntaje_out_of_range(auth_client, competencia, estudiante, director_semillero):
    ev = _make_evaluacion(
        competencia, estudiante, director_semillero,
        tipo=Evaluacion.TipoChoices.HETEROEVALUACION,
    )
    client = auth_client(director_semillero)
    payload = {'puntaje': '9.9', 'nivel_alcanzado': Evaluacion.NivelAlcanzadoChoices.BASICO}
    resp = client.post(f'{URL}{ev.id}/calificar/', payload, format='json')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_calificar_post_requires_puntaje_and_nivel(auth_client, competencia, estudiante, director_semillero):
    ev = _make_evaluacion(
        competencia, estudiante, director_semillero,
        tipo=Evaluacion.TipoChoices.HETEROEVALUACION,
    )
    client = auth_client(director_semillero)
    resp = client.post(f'{URL}{ev.id}/calificar/', {'observaciones': 'Solo nota.'}, format='json')
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_calificar_patch_partial(auth_client, competencia, estudiante, director_semillero):
    ev = _make_evaluacion(
        competencia, estudiante, director_semillero,
        tipo=Evaluacion.TipoChoices.HETEROEVALUACION,
        puntaje='3.0',
        nivel_alcanzado=Evaluacion.NivelAlcanzadoChoices.INTERMEDIO,
    )
    client = auth_client(director_semillero)
    resp = client.patch(f'{URL}{ev.id}/calificar/', {'observaciones': 'Actualizado.'}, format='json')
    assert resp.status_code == 200, resp.content
    ev.refresh_from_db()
    assert ev.observaciones == 'Actualizado.'
