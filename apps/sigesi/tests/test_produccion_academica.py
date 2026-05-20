"""Smoke tests for /api/v1/core/producciones-academicas/."""
import pytest


URL = '/api/v1/core/producciones-academicas/'


def _payload(proyecto, semillero, autor):
    return {
        'titulo': 'Paper IA',
        'tipo': 'articulo',
        'descripcion': 'desc',
        'proyecto': proyecto.id,
        'semillero': semillero.id,
        'autores': [autor.id],
        'estado': 'en_elaboracion',
    }


@pytest.mark.django_db
def test_admin_can_create_produccion(
    auth_client, admin_user, proyecto, semillero_aprobado, lider_estudiantil
):
    client = auth_client(admin_user)
    resp = client.post(
        URL, _payload(proyecto, semillero_aprobado, lider_estudiantil), format='json'
    )
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_proyecto_director_can_create_for_their_project(
    auth_client, director_semillero, proyecto, semillero_aprobado, lider_estudiantil
):
    """director_semillero is the project's `director` fixture-side."""
    client = auth_client(director_semillero)
    resp = client.post(
        URL, _payload(proyecto, semillero_aprobado, lider_estudiantil), format='json'
    )
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_create_produccion_returns_403(
    auth_client, otro_estudiante, proyecto, semillero_aprobado
):
    """Plain estudiante who is not the project's director or lider → 403."""
    client = auth_client(otro_estudiante)
    resp = client.post(
        URL, _payload(proyecto, semillero_aprobado, otro_estudiante), format='json'
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_other_authenticated_user_can_list(
    auth_client, otro_estudiante, proyecto, semillero_aprobado, lider_estudiantil
):
    """Reads are unscoped — any authenticated user can list productions."""
    from apps.sigesi.models import ProduccionAcademica
    p = ProduccionAcademica.objects.create(
        titulo='X', tipo='articulo', proyecto=proyecto, semillero=semillero_aprobado,
    )
    p.autores.set([lider_estudiantil])

    client = auth_client(otro_estudiante)
    resp = client.get(URL)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_without_proyecto_returns_400(
    auth_client, admin_user, semillero_aprobado, lider_estudiantil
):
    client = auth_client(admin_user)
    payload = {
        'titulo': 'X',
        'tipo': 'articulo',
        'semillero': semillero_aprobado.id,
        'autores': [lider_estudiantil.id],
    }
    resp = client.post(URL, payload, format='json')
    assert resp.status_code == 400
    assert 'proyecto' in resp.json()


@pytest.mark.django_db
def test_create_when_semillero_not_aprobado_returns_400(
    auth_client, director_semillero, semillero_sin_aprobar, lider_estudiantil
):
    """Even the project director can't write if the semillero isn't approved."""
    from apps.sigesi.models import Proyecto
    p = Proyecto.objects.create(
        titulo='Pno', codigo='PNO4', descripcion='d', objetivo_general='o',
        director=director_semillero,
    )
    p.semilleros.set([semillero_sin_aprobar])

    client = auth_client(director_semillero)
    resp = client.post(URL, {
        'titulo': 'X',
        'tipo': 'articulo',
        'proyecto': p.id,
        'semillero': semillero_sin_aprobar.id,
        'autores': [lider_estudiantil.id],
    }, format='json')
    assert resp.status_code == 400
    assert 'aval aprobado' in resp.content.decode().lower()
