"""Smoke tests for /api/v1/core/actividades/ — aval gate + role gates."""
from datetime import date

import pytest


URL = '/api/v1/core/actividades/'


@pytest.mark.django_db
def test_director_can_create_actividad_on_aprobado_proyecto(
    auth_client, director_semillero, proyecto, lider_estudiantil
):
    client = auth_client(director_semillero)
    resp = client.post(URL, {
        'proyecto': proyecto.id,
        'titulo': 'Tarea 1',
        'descripcion': 'desc',
        'responsable': lider_estudiantil.id,
        'fecha_inicio': str(date.today()),
        'fecha_fin': str(date.today()),
        'estado': 'pendiente',
        'porcentaje_avance': 0,
    }, format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_create_actividad_when_semillero_not_aprobado_returns_400(
    auth_client, director_semillero, semillero_sin_aprobar, lider_estudiantil
):
    """Build a proyecto on a sin_aprobar semillero, then try to create an actividad."""
    from apps.sigesi.models import Proyecto
    p = Proyecto.objects.create(
        titulo='Pno', codigo='PNO', descripcion='d', objetivo_general='o',
        director=director_semillero,
    )
    p.semilleros.set([semillero_sin_aprobar])

    client = auth_client(director_semillero)
    resp = client.post(URL, {
        'proyecto': p.id,
        'titulo': 'X',
        'descripcion': 'X',
        'responsable': lider_estudiantil.id,
        'fecha_inicio': str(date.today()),
        'fecha_fin': str(date.today()),
        'estado': 'pendiente',
        'porcentaje_avance': 0,
    }, format='json')
    assert resp.status_code == 400
    assert 'aval aprobado' in resp.content.decode().lower()


@pytest.mark.django_db
def test_estudiante_is_read_only_on_actividad(
    auth_client, estudiante, proyecto, lider_estudiantil
):
    client = auth_client(estudiante)
    resp = client.post(URL, {
        'proyecto': proyecto.id,
        'titulo': 'X',
        'descripcion': 'X',
        'responsable': lider_estudiantil.id,
        'fecha_inicio': str(date.today()),
        'fecha_fin': str(date.today()),
        'estado': 'pendiente',
        'porcentaje_avance': 0,
    }, format='json')
    assert resp.status_code == 403
