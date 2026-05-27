"""Smoke tests para /api/v1/core/competencias-investigativas/ — CRUD, alcance, aval.

Cubre: happy-path de creación (admin), 403 de creación para roles no autorizados,
matriz de actualización/eliminación por rol, lectura por rol permitido, filtro de
alcance por rol, aval gate sobre el semillero, y la forma anidada del semillero en
lectura.
"""
from datetime import date

import pytest

from apps.sigesi.models import (
    CompetenciaInvestigativa,
    GrupoInvestigacion,
    Semillero,
)


URL = '/api/v1/core/competencias-investigativas/'


def _payload(semillero, **overrides):
    data = {
        'semillero': semillero.id,
        'nombre': 'Redacción científica',
        'descripcion': 'Capacidad de escribir artículos.',
        'nivel': CompetenciaInvestigativa.NivelChoices.BASICO,
        'indicadores': 'Indicadores de logro.',
    }
    data.update(overrides)
    return data


def _make_competencia(semillero, **overrides):
    defaults = dict(
        nombre='Redacción científica',
        descripcion='Capacidad de escribir artículos.',
        nivel=CompetenciaInvestigativa.NivelChoices.BASICO,
        indicadores='Indicadores de logro.',
    )
    defaults.update(overrides)
    return CompetenciaInvestigativa.objects.create(semillero=semillero, **defaults)


def _filas(resp):
    """Devuelve las filas de la respuesta, sea paginada o no."""
    data = resp.data
    return data['results'] if isinstance(data, dict) and 'results' in data else data


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
# Create: solo Administrador
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_admin_can_create(auth_client, admin_user, semillero_aprobado):
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_director_grupo_cannot_create(auth_client, director_grupo, semillero_aprobado):
    client = auth_client(director_grupo)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_director_semillero_cannot_create(auth_client, director_semillero, semillero_aprobado):
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_lider_cannot_create(auth_client, lider_estudiantil, semillero_aprobado):
    client = auth_client(lider_estudiantil)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_create(auth_client, estudiante, semillero_aprobado):
    client = auth_client(estudiante)
    resp = client.post(URL, _payload(semillero_aprobado), format='json')
    assert resp.status_code == 403, resp.content


# --------------------------------------------------------------------------- #
# Update: Admin y Director de Semillero (de su semillero); el resto no
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_admin_can_update(auth_client, admin_user, semillero_aprobado):
    comp = _make_competencia(semillero_aprobado)
    client = auth_client(admin_user)
    resp = client.patch(f'{URL}{comp.id}/', {'nombre': 'Nuevo'}, format='json')
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
def test_director_semillero_can_update_own(auth_client, director_semillero, semillero_aprobado):
    comp = _make_competencia(semillero_aprobado)
    client = auth_client(director_semillero)
    resp = client.patch(f'{URL}{comp.id}/', {'nombre': 'Nuevo'}, format='json')
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
def test_director_grupo_cannot_update(auth_client, director_grupo, semillero_aprobado):
    comp = _make_competencia(semillero_aprobado)
    client = auth_client(director_grupo)
    resp = client.patch(f'{URL}{comp.id}/', {'nombre': 'Nuevo'}, format='json')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_update(auth_client, estudiante, semillero_aprobado):
    comp = _make_competencia(semillero_aprobado)
    client = auth_client(estudiante)
    resp = client.patch(f'{URL}{comp.id}/', {'nombre': 'Nuevo'}, format='json')
    assert resp.status_code == 403, resp.content


@pytest.mark.django_db
def test_director_semillero_cannot_update_other_semillero(
    auth_client, director_semillero, semillero_otro_grupo
):
    comp = _make_competencia(semillero_otro_grupo)
    client = auth_client(director_semillero)
    resp = client.patch(f'{URL}{comp.id}/', {'nombre': 'Nuevo'}, format='json')
    # La competencia queda fuera del queryset del director de semillero -> 404.
    assert resp.status_code == 404, resp.content


# --------------------------------------------------------------------------- #
# Delete: solo Administrador
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_admin_can_delete(auth_client, admin_user, semillero_aprobado):
    comp = _make_competencia(semillero_aprobado)
    client = auth_client(admin_user)
    resp = client.delete(f'{URL}{comp.id}/')
    assert resp.status_code == 204, resp.content


@pytest.mark.django_db
def test_director_semillero_cannot_delete(auth_client, director_semillero, semillero_aprobado):
    comp = _make_competencia(semillero_aprobado)
    client = auth_client(director_semillero)
    resp = client.delete(f'{URL}{comp.id}/')
    assert resp.status_code == 403, resp.content


# --------------------------------------------------------------------------- #
# Read: todos los roles permitidos pueden listar
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
@pytest.mark.parametrize('rol', ['admin_user', 'director_grupo', 'director_semillero',
                                 'lider_estudiantil', 'estudiante'])
def test_roles_can_read(auth_client, request, rol, semillero_aprobado):
    _make_competencia(semillero_aprobado)
    user = request.getfixturevalue(rol)
    client = auth_client(user)
    resp = client.get(URL)
    assert resp.status_code == 200, resp.content


# --------------------------------------------------------------------------- #
# Filtro de alcance por rol
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_director_grupo_only_sees_own_group(auth_client, director_grupo,
                                             semillero_aprobado, semillero_otro_grupo):
    _make_competencia(semillero_aprobado)
    _make_competencia(semillero_otro_grupo)
    client = auth_client(director_grupo)
    resp = client.get(URL)
    assert resp.status_code == 200
    ids = {row['semillero']['id'] for row in _filas(resp)}
    assert semillero_aprobado.id in ids
    assert semillero_otro_grupo.id not in ids


@pytest.mark.django_db
def test_director_semillero_only_sees_own(auth_client, director_semillero,
                                          semillero_aprobado, semillero_otro_grupo):
    _make_competencia(semillero_aprobado)
    _make_competencia(semillero_otro_grupo)
    client = auth_client(director_semillero)
    resp = client.get(URL)
    assert resp.status_code == 200
    ids = {row['semillero']['id'] for row in _filas(resp)}
    assert semillero_aprobado.id in ids
    assert semillero_otro_grupo.id not in ids


# --------------------------------------------------------------------------- #
# Aval gate sobre el semillero
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_director_semillero_update_blocked_by_aval(
    auth_client, director_semillero, semillero_sin_aprobar
):
    comp = _make_competencia(semillero_sin_aprobar)
    client = auth_client(director_semillero)
    resp = client.patch(f'{URL}{comp.id}/', {'nombre': 'Nuevo'}, format='json')
    # El semillero no tiene aval aprobado -> 400 por el aval gate.
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_admin_bypasses_aval_gate(auth_client, admin_user, semillero_sin_aprobar):
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(semillero_sin_aprobar), format='json')
    assert resp.status_code == 201, resp.content


# --------------------------------------------------------------------------- #
# Forma de lectura: semillero anidado
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_retrieve_embeds_semillero(auth_client, admin_user, semillero_aprobado):
    comp = _make_competencia(semillero_aprobado)
    client = auth_client(admin_user)
    resp = client.get(f'{URL}{comp.id}/')
    assert resp.status_code == 200, resp.content
    assert isinstance(resp.data['semillero'], dict)
    assert resp.data['semillero']['id'] == semillero_aprobado.id
    assert resp.data['semillero']['nombre'] == semillero_aprobado.nombre
