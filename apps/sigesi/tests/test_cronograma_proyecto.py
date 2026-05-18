"""Smoke tests for /api/v1/core/cronograma-proyecto/ — CRUD + cumplimiento %."""
from datetime import date

import pytest

from apps.sigesi.models import CronogramaProyecto


URL = '/api/v1/core/cronograma-proyecto/'


@pytest.mark.django_db
def test_director_can_create_cronograma_row(auth_client, director_semillero, proyecto):
    client = auth_client(director_semillero)
    resp = client.post(URL, {
        'proyecto': proyecto.id,
        'actividad': 'Diseño',
        'descripcion_actividad': 'desc',
        'fecha_inicio': str(date.today()),
        'fecha_fin': str(date.today()),
        'fecha_entrega': str(date.today()),
        'estado_actividad': 'pendiente',
    }, format='multipart')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_porcentaje_cumplimiento_returns_correct_ratio(
    auth_client, director_semillero, proyecto
):
    """Seed 4 rows, 1 completed → 25.0%."""
    for estado in ('pendiente', 'pendiente', 'pendiente', 'completada'):
        CronogramaProyecto.objects.create(
            proyecto=proyecto,
            actividad=f'X-{estado}',
            descripcion_actividad='d',
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
            fecha_entrega=date.today(),
            estado_actividad=estado,
        )

    client = auth_client(director_semillero)
    resp = client.get(f'{URL}porcentaje-cumplimiento/?proyecto={proyecto.id}')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body['total_actividades'] == 4
    assert body['completadas'] == 1
    assert body['porcentaje_cumplimiento'] == 25.0


@pytest.mark.django_db
def test_porcentaje_cumplimiento_without_proyecto_returns_400(
    auth_client, director_semillero
):
    client = auth_client(director_semillero)
    resp = client.get(f'{URL}porcentaje-cumplimiento/')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_create_cronograma_when_semillero_not_aprobado_returns_400(
    auth_client, director_semillero, semillero_sin_aprobar
):
    from apps.sigesi.models import Proyecto
    p = Proyecto.objects.create(
        titulo='Pno', codigo='PNO2', descripcion='d', objetivo_general='o',
        director=director_semillero,
    )
    p.semilleros.set([semillero_sin_aprobar])

    client = auth_client(director_semillero)
    resp = client.post(URL, {
        'proyecto': p.id,
        'actividad': 'X',
        'descripcion_actividad': 'X',
        'fecha_inicio': str(date.today()),
        'fecha_fin': str(date.today()),
        'fecha_entrega': str(date.today()),
        'estado_actividad': 'pendiente',
    }, format='multipart')
    assert resp.status_code == 400
