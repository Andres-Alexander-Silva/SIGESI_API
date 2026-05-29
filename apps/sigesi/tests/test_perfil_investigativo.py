"""Smoke tests for /api/v1/core/perfiles-investigativos/ — RBAC scoping.

El acceso de lectura por rol se resuelve vía la matrícula del estudiante en
semilleros: el Director de Grupo ve los perfiles de los estudiantes de los
semilleros de su grupo, el Director de Semillero los de su semillero, y el
Estudiante solo el suyo. Solo el Administrador escribe.
"""
import pytest

from apps.sigesi.models import MatriculaSemillero, PerfilInvestigativo


URL = '/api/v1/core/perfiles-investigativos/'


def _crear_perfil(estudiante):
    """Crea un PerfilInvestigativo mínimo para el estudiante dado."""
    return PerfilInvestigativo.objects.create(
        estudiante=estudiante,
        resumen='Resumen de prueba.',
    )


def _matricular(estudiante, semillero):
    """Matricula activamente al estudiante en el semillero."""
    return MatriculaSemillero.objects.create(
        estudiante=estudiante,
        semillero=semillero,
        semestre='2025-1',
    )


@pytest.mark.django_db
def test_admin_can_create_perfil(auth_client, admin_user, estudiante):
    client = auth_client(admin_user)
    resp = client.post(URL, {
        'estudiante': estudiante.id,
        'resumen': 'Buen desempeño investigativo.',
        'fortalezas': 'Análisis de datos.',
        'areas_mejora': 'Redacción académica.',
    }, format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_create_perfil_requires_estudiante_role(auth_client, admin_user, director_grupo):
    """El usuario asignado debe tener el rol de estudiante."""
    client = auth_client(admin_user)
    resp = client.post(URL, {
        'estudiante': director_grupo.id,
        'resumen': 'x',
    }, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_admin_sees_all_perfiles(auth_client, admin_user, estudiante, otro_estudiante):
    perfil = _crear_perfil(estudiante)
    _crear_perfil(otro_estudiante)
    client = auth_client(admin_user)
    resp = client.get(URL)
    assert resp.status_code == 200
    ids = [p['id'] for p in resp.json()['results']]
    assert perfil.id in ids
    assert len(ids) == 2


@pytest.mark.django_db
def test_estudiante_only_sees_own_perfil(
    auth_client, estudiante, otro_estudiante
):
    propio = _crear_perfil(estudiante)
    ajeno = _crear_perfil(otro_estudiante)
    client = auth_client(estudiante)
    resp = client.get(URL)
    assert resp.status_code == 200
    ids = [p['id'] for p in resp.json()['results']]
    assert propio.id in ids
    assert ajeno.id not in ids


@pytest.mark.django_db
def test_director_semillero_sees_only_enrolled_students(
    auth_client, director_semillero, estudiante, otro_estudiante, semillero_aprobado
):
    """Ve el perfil del matriculado en su semillero, no el del no matriculado."""
    matriculado = _crear_perfil(estudiante)
    no_matriculado = _crear_perfil(otro_estudiante)
    _matricular(estudiante, semillero_aprobado)

    client = auth_client(director_semillero)
    resp = client.get(URL)
    assert resp.status_code == 200
    ids = [p['id'] for p in resp.json()['results']]
    assert matriculado.id in ids
    assert no_matriculado.id not in ids


@pytest.mark.django_db
def test_director_grupo_sees_students_of_group_semilleros(
    auth_client, director_grupo, estudiante, otro_estudiante, semillero_aprobado
):
    """Ve el perfil del estudiante matriculado en un semillero de su grupo."""
    matriculado = _crear_perfil(estudiante)
    no_matriculado = _crear_perfil(otro_estudiante)
    _matricular(estudiante, semillero_aprobado)

    client = auth_client(director_grupo)
    resp = client.get(URL)
    assert resp.status_code == 200
    ids = [p['id'] for p in resp.json()['results']]
    assert matriculado.id in ids
    assert no_matriculado.id not in ids


@pytest.mark.django_db
def test_director_semillero_cannot_create(auth_client, director_semillero, estudiante):
    client = auth_client(director_semillero)
    resp = client.post(URL, {'estudiante': estudiante.id, 'resumen': 'x'}, format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_estudiante_cannot_create(auth_client, estudiante):
    client = auth_client(estudiante)
    resp = client.post(URL, {'estudiante': estudiante.id, 'resumen': 'x'}, format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_lider_estudiantil_sees_only_own_perfil(
    auth_client, lider_estudiantil, estudiante
):
    """El Líder Estudiantil solo lee su propio perfil, no el de otros."""
    propio = _crear_perfil(lider_estudiantil)
    ajeno = _crear_perfil(estudiante)
    client = auth_client(lider_estudiantil)

    resp = client.get(URL)
    assert resp.status_code == 200
    ids = [p['id'] for p in resp.json()['results']]
    assert propio.id in ids
    assert ajeno.id not in ids


@pytest.mark.django_db
def test_lider_estudiantil_cannot_create(auth_client, lider_estudiantil, estudiante):
    client = auth_client(lider_estudiantil)
    resp = client.post(
        URL, {'estudiante': estudiante.id, 'resumen': 'x'}, format='json'
    )
    assert resp.status_code == 403
