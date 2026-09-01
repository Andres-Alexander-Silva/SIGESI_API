"""Regresión: /api/v1/core/evaluaciones-proyecto/ lanzaba 500 (AttributeError)
para todo rol distinto de administrador porque el queryset referenciaba
``User.RolChoices.DOCENTE``, un rol que nunca existió en el modelo.
"""
import pytest

URL = '/api/v1/core/evaluaciones-proyecto/'


@pytest.mark.django_db
@pytest.mark.parametrize('role_fixture', ['admin_user', 'director_grupo', 'director_semillero', 'estudiante', 'lider_estudiantil'])
def test_listar_evaluaciones_no_falla_para_ningun_rol(request, auth_client, role_fixture, proyecto):
    user = request.getfixturevalue(role_fixture)
    client = auth_client(user)
    resp = client.get(URL)
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
def test_director_semillero_puede_evaluar_su_proyecto(auth_client, director_semillero, proyecto):
    client = auth_client(director_semillero)
    resp = client.post(URL, {
        'proyecto': proyecto.id,
        'calificacion': '4.5',
        'estado_proyecto': proyecto.estado,
        'observaciones': 'Buen avance del proyecto.',
    }, format='json')
    assert resp.status_code == 201, resp.content
