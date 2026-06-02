"""Smoke tests for /api/v1/core/dashboard/indicadores/ — RBAC scoping."""
import pytest
from datetime import date

from apps.sigesi.models import (
    Proyecto,
    Semillero,
    User,
    GrupoInvestigacion,
)


URL = '/api/v1/core/dashboard/indicadores/'


@pytest.fixture
def proyecto_activo(db, semillero_aprobado):
    """Proyecto en_ejecucion vinculado al semillero aprobado."""
    p = Proyecto.objects.create(
        titulo='Proyecto Activo',
        codigo='PA1',
        descripcion='desc',
        objetivo_general='og',
        estado=Proyecto.EstadoChoices.EN_EJECUCION,
    )
    p.semilleros.add(semillero_aprobado)
    return p


@pytest.fixture
def proyecto_cerrado(db, semillero_aprobado):
    """Proyecto cerrado vinculado al semillero aprobado."""
    p = Proyecto.objects.create(
        titulo='Proyecto Cerrado',
        codigo='PC1',
        descripcion='desc',
        objetivo_general='og',
        estado=Proyecto.EstadoChoices.CERRADO,
    )
    p.semilleros.add(semillero_aprobado)
    return p


@pytest.fixture
def proyecto_en_resultados(db, semillero_aprobado):
    """Proyecto en_resultados vinculado al semillero aprobado."""
    p = Proyecto.objects.create(
        titulo='Proyecto Resultados',
        codigo='PR1',
        descripcion='desc',
        objetivo_general='og',
        estado=Proyecto.EstadoChoices.EN_RESULTADOS,
    )
    p.semilleros.add(semillero_aprobado)
    return p


@pytest.mark.django_db
def test_admin_happy_path(auth_client, admin_user, semillero_aprobado,
                          proyecto_activo, proyecto_cerrado, proyecto_en_resultados):
    """Administrador recibe indicadores correctos."""
    client = auth_client(admin_user)
    resp = client.get(URL, {'semillero': semillero_aprobado.id})
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data['success'] is True
    assert data['data']['proyectos_activos'] == 2
    assert data['data']['proyectos_finalizados'] == 1


@pytest.mark.django_db
def test_admin_missing_semillero_returns_400(auth_client, admin_user):
    """Sin semillero → 400."""
    client = auth_client(admin_user)
    resp = client.get(URL)
    assert resp.status_code == 400
    assert 'semillero es requerido' in resp.json()['error']


@pytest.mark.django_db
def test_admin_invalid_semillero_returns_400(auth_client, admin_user):
    """semillero no entero → 400."""
    client = auth_client(admin_user)
    resp = client.get(URL, {'semillero': 'abc'})
    assert resp.status_code == 400
    assert 'debe ser un entero' in resp.json()['error']


@pytest.mark.django_db
def test_director_grupo_can_query_own_group(
    auth_client, director_grupo, grupo, semillero_aprobado,
    proyecto_activo, proyecto_cerrado
):
    """director_grupo puede consultar semilleros de su grupo."""
    client = auth_client(director_grupo)
    resp = client.get(URL, {'semillero': semillero_aprobado.id})
    assert resp.status_code == 200, resp.content
    assert resp.json()['success'] is True


@pytest.mark.django_db
def test_director_grupo_cannot_query_unrelated_semillero(
    auth_client, director_grupo, programa, linea
):
    """director_grupo recibe 403 para semillero de otro grupo."""
    otro_dir = User.objects.create(
        username='otro_dir_g2', cedula='C00991', roles=['director_grupo'],
        correo_personal='odg2@example.com', email='odg2@inst.edu',
        first_name='Otro', last_name='DirG2',
    )
    otro_dir.set_password('x')
    otro_dir.save()
    otro_grupo = GrupoInvestigacion.objects.create(
        nombre='Grupo Ajeno G2', codigo='GA91',
        fecha_creacion=date.today(),
        programa_academico=programa,
        director=otro_dir,
    )
    otro_semillero = Semillero.objects.create(
        nombre='Semillero Ajeno G2', codigo='SA91',
        objetivo='otro', fecha_creacion=date.today(),
        grupo_investigacion=otro_grupo,
        director=otro_dir,
        estado_aval=Semillero.EstadoAvalChoices.APROBADO,
    )
    client = auth_client(director_grupo)
    resp = client.get(URL, {'semillero': otro_semillero.id})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_director_semillero_can_query_own_semillero(
    auth_client, director_semillero, semillero_aprobado,
    proyecto_activo
):
    """director_semillero puede consultar sus propios semilleros."""
    client = auth_client(director_semillero)
    resp = client.get(URL, {'semillero': semillero_aprobado.id})
    assert resp.status_code == 200, resp.content
    assert resp.json()['success'] is True


@pytest.mark.django_db
def test_director_semillero_cannot_query_others_semillero(
    auth_client, director_semillero, grupo, programa, linea
):
    """director_semillero recibe 403 al consultar semillero que no dirige."""
    otro_dir = User.objects.create(
        username='otro_dir_s2', cedula='C00990', roles=['director_semillero'],
        correo_personal='ods3@example.com', email='ods3@inst.edu',
        first_name='Otro', last_name='DirS2',
    )
    otro_dir.set_password('x')
    otro_dir.save()
    otro_semillero = Semillero.objects.create(
        nombre='Semillero Ajeno S2', codigo='SA90',
        objetivo='otro', fecha_creacion=date.today(),
        grupo_investigacion=grupo,
        director=otro_dir,
        estado_aval=Semillero.EstadoAvalChoices.APROBADO,
    )
    client = auth_client(director_semillero)
    resp = client.get(URL, {'semillero': otro_semillero.id})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_estudiante_cannot_access(auth_client, estudiante, semillero_aprobado):
    """estudiante → 403."""
    client = auth_client(estudiante)
    resp = client.get(URL, {'semillero': semillero_aprobado.id})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_lider_estudiantil_cannot_access(auth_client, lider_estudiantil, semillero_aprobado):
    """lider_estudiantil → 403."""
    client = auth_client(lider_estudiantil)
    resp = client.get(URL, {'semillero': semillero_aprobado.id})
    assert resp.status_code == 403