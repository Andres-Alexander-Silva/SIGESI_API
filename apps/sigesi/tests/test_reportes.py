"""Regresión: los endpoints de reportes e informes lanzaban 500
(AttributeError) para todo rol distinto de administrador porque referenciaban
``User.RolChoices.DOCENTE`` y ``User.RolChoices.DIRECTOR_PROGRAMA``, roles que
nunca existieron en el modelo.
"""
import pytest

REPORTE_PROYECTOS_URL = '/api/v1/reportes/proyectos/'
REPORTE_SEMILLEROS_URL = '/api/v1/reportes/semilleros/'
INFORMES_URL = '/api/v1/reportes/'

ROLES = ['admin_user', 'director_grupo', 'director_semillero', 'estudiante', 'lider_estudiantil']


@pytest.mark.django_db
@pytest.mark.parametrize('role_fixture', ROLES)
def test_reporte_proyectos_no_falla_para_ningun_rol(request, auth_client, role_fixture, proyecto):
    user = request.getfixturevalue(role_fixture)
    client = auth_client(user)
    resp = client.get(REPORTE_PROYECTOS_URL)
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
@pytest.mark.parametrize('role_fixture', ROLES)
def test_reporte_semilleros_no_falla_para_ningun_rol(request, auth_client, role_fixture, semillero_aprobado):
    user = request.getfixturevalue(role_fixture)
    client = auth_client(user)
    resp = client.get(REPORTE_SEMILLEROS_URL)
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
@pytest.mark.parametrize('role_fixture', ROLES)
def test_listar_informes_no_falla_para_ningun_rol(request, auth_client, role_fixture, semillero_aprobado):
    user = request.getfixturevalue(role_fixture)
    client = auth_client(user)
    resp = client.get(INFORMES_URL)
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
def test_director_semillero_puede_generar_informe(auth_client, director_semillero, semillero_aprobado):
    client = auth_client(director_semillero)
    resp = client.post(f'{INFORMES_URL}generar/', {
        'semillero_id': semillero_aprobado.id,
        'tipo': 'semestral',
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 201, resp.content
