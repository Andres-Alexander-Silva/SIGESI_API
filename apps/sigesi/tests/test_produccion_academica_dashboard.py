"""Smoke tests for /api/v1/core/produccion-academica/dashboard/ — RBAC scoping."""
import pytest
from datetime import date

from apps.sigesi.models import (
    ProduccionAcademica,
    MatriculaSemillero,
    User,
)


URL = '/api/v1/core/produccion-academica/dashboard/'


@pytest.fixture
def linea2(db):
    from apps.sigesi.models import LineaInvestigacion
    return LineaInvestigacion.objects.create(nombre='Ingeniería de Software')


@pytest.fixture
def autor1(db, semillero_aprobado):
    u = User.objects.create(
        username='autor1', cedula='C00111', roles=['estudiante'],
        correo_personal='autor1@example.com', email='autor1@inst.edu',
        first_name='A', last_name='One',
    )
    u.set_password('x')
    u.save()
    MatriculaSemillero.objects.create(
        estudiante=u, semillero=semillero_aprobado,
        semestre='2024-1', estado=MatriculaSemillero.EstadoChoices.ACTIVA,
    )
    return u


@pytest.fixture
def autor2(db, semillero_aprobado):
    u = User.objects.create(
        username='autor2', cedula='C00112', roles=['estudiante'],
        correo_personal='autor2@example.com', email='autor2@inst.edu',
        first_name='A', last_name='Two',
    )
    u.set_password('x')
    u.save()
    MatriculaSemillero.objects.create(
        estudiante=u, semillero=semillero_aprobado,
        semestre='2024-1', estado=MatriculaSemillero.EstadoChoices.ACTIVA,
    )
    return u


@pytest.fixture
def produccion1(db, semillero_aprobado, autor1, linea):
    """Producción Jan 2024, linea Inteligencia Artificial, autor1."""
    p = ProduccionAcademica.objects.create(
        titulo='Producción uno',
        tipo=ProduccionAcademica.TipoChoices.ARTICULO,
        semillero=semillero_aprobado,
        linea_investigacion=linea,
        fecha_publicacion=date(2024, 1, 15),
        estado=ProduccionAcademica.EstadoChoices.PUBLICADO,
    )
    p.autores.add(autor1)
    return p


@pytest.fixture
def produccion2(db, semillero_aprobado, autor2, linea2):
    """Producción Jan 2024, linea Ing. Software, autor2."""
    p = ProduccionAcademica.objects.create(
        titulo='Producción dos',
        tipo=ProduccionAcademica.TipoChoices.PONENCIA,
        semillero=semillero_aprobado,
        linea_investigacion=linea2,
        fecha_publicacion=date(2024, 1, 20),
        estado=ProduccionAcademica.EstadoChoices.PUBLICADO,
    )
    p.autores.add(autor2)
    return p


@pytest.mark.django_db
def test_admin_can_query_dashboard(
    auth_client, admin_user, semillero_aprobado, produccion1, produccion2
):
    """Administrador puede consultar cualquier semillero."""
    client = auth_client(admin_user)
    resp = client.post(URL, {
        'semillero_id': semillero_aprobado.id,
        'periodo': '2024-1',
        'cohorte': '2024',
    }, format='json')
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data['success'] is True
    assert len(data['data']) == 2


@pytest.mark.django_db
def test_admin_missing_semillero_id_returns_400(auth_client, admin_user):
    client = auth_client(admin_user)
    resp = client.post(URL, {'periodo': '2024-1'}, format='json')
    assert resp.status_code == 400
    assert 'semillero_id es requerido' in resp.json()['error']


@pytest.mark.django_db
def test_director_grupo_can_query_own_group_semillero(
    auth_client, director_grupo, grupo, semillero_aprobado,
    produccion1, produccion2
):
    """director_grupo puede consultar semilleros de su grupo de investigación."""
    client = auth_client(director_grupo)
    resp = client.post(URL, {
        'semillero_id': semillero_aprobado.id,
        'cohorte': '2024',
    }, format='json')
    assert resp.status_code == 200, resp.content
    assert resp.json()['success'] is True


@pytest.mark.django_db
def test_director_grupo_cannot_query_unrelated_semillero(
    auth_client, director_grupo, programa, linea
):
    """director_grupo recibe 403 al consultar un semillero de otro grupo."""
    from apps.sigesi.models import GrupoInvestigacion, Semillero
    # Crear otro director de grupo
    otro_director = User.objects.create(
        username='otro_dir_grupo', cedula='C00998', roles=['director_grupo'],
        correo_personal='odg@example.com', email='odg@inst.edu',
        first_name='Otro', last_name='DirGrupo',
    )
    otro_director.set_password('x')
    otro_director.save()
    # Grupo con director distinto
    otro_grupo = GrupoInvestigacion.objects.create(
        nombre='Grupo Ajeno', codigo='GA99',
        fecha_creacion=date.today(),
        programa_academico=programa,
        director=otro_director,
    )
    otro_semillero = Semillero.objects.create(
        nombre='Semillero Ajeno', codigo='SA99',
        objetivo='otro', fecha_creacion=date.today(),
        grupo_investigacion=otro_grupo,
        director=otro_director,
        estado_aval=Semillero.EstadoAvalChoices.APROBADO,
    )
    client = auth_client(director_grupo)
    resp = client.post(URL, {
        'semillero_id': otro_semillero.id,
        'cohorte': '2024',
    }, format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_director_semillero_can_query_own_semillero(
    auth_client, director_semillero, semillero_aprobado,
    produccion1, produccion2
):
    """director_semillero puede consultar sus propios semilleros."""
    client = auth_client(director_semillero)
    resp = client.post(URL, {
        'semillero_id': semillero_aprobado.id,
        'cohorte': '2024',
    }, format='json')
    assert resp.status_code == 200, resp.content
    assert resp.json()['success'] is True


@pytest.mark.django_db
def test_director_semillero_cannot_query_others_semillero(
    auth_client, director_semillero, grupo, programa, linea
):
    """director_semillero recibe 403 al consultar un semillero que no dirige."""
    otro_dir = User.objects.create(
        username='otro_dir_sem2', cedula='C00996', roles=['director_semillero'],
        correo_personal='ods2@example.com', email='ods2@inst.edu',
        first_name='Otro', last_name='DirSem2',
    )
    otro_dir.set_password('x')
    otro_dir.save()
    otro_semillero = Semillero.objects.create(
        nombre='Semillero Ajeno', codigo='SA97',
        objetivo='otro', fecha_creacion=date.today(),
        grupo_investigacion=grupo,
        director=otro_dir,
        estado_aval=Semillero.EstadoAvalChoices.APROBADO,
    )
    client = auth_client(director_semillero)
    resp = client.post(URL, {
        'semillero_id': otro_semillero.id,
        'cohorte': '2024',
    }, format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_estudiante_cannot_access_dashboard(
    auth_client, estudiante, semillero_aprobado
):
    """estudiante recibe 403 — rol no habilitado."""
    client = auth_client(estudiante)
    resp = client.post(URL, {
        'semillero_id': semillero_aprobado.id,
    }, format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_lider_estudiantil_cannot_access_dashboard(
    auth_client, lider_estudiantil, semillero_aprobado
):
    """lider_estudiantil recibe 403 — rol no habilitado."""
    client = auth_client(lider_estudiantil)
    resp = client.post(URL, {
        'semillero_id': semillero_aprobado.id,
    }, format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_invalid_periodo_returns_400(auth_client, admin_user, semillero_aprobado):
    client = auth_client(admin_user)
    resp = client.post(URL, {
        'semillero_id': semillero_aprobado.id,
        'periodo': 'invalid-format',
    }, format='json')
    assert resp.status_code == 400
    assert 'YYYY-1' in resp.json()['error']


@pytest.mark.django_db
def test_response_shape_with_producciones(
    auth_client, admin_user, semillero_aprobado, produccion1, produccion2,
    autor1, autor2
):
    """Verifica que participacion y produccion_academica sean correctos."""
    client = auth_client(admin_user)
    resp = client.post(URL, {
        'semillero_id': semillero_aprobado.id,
        'periodo': '2024-1',
        'cohorte': '2024',
    }, format='json')
    assert resp.status_code == 200
    data = resp.json()['data']
    # Buscar la línea de Ing. Software (linea2)
    row = next((r for r in data if r['linea_investigacion'] == 'Ingeniería de Software'), None)
    assert row is not None
    assert row['produccion_academica'] == 1
    assert row['participacion'] == 1