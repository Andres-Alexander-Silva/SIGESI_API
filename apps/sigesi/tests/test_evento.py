"""Smoke tests for /api/v1/core/eventos/ — RBAC (admin escribe, resto lee).

Los eventos son administrados solo por el Administrador; cualquier otro rol
autenticado tiene acceso de solo lectura (``AdminOrReadOnlyPermission``).
"""
from datetime import date, timedelta

import pytest

from apps.sigesi.models import Evento


URL = '/api/v1/core/eventos/'


def _crear_evento(nombre='Congreso de IA'):
    """Crea un Evento mínimo válido."""
    return Evento.objects.create(
        nombre=nombre,
        fecha_inicio=date.today(),
        fecha_fin=date.today() + timedelta(days=2),
    )


def _payload(**overrides):
    data = {
        'nombre': 'Simposio de Investigación',
        'descripcion': 'Encuentro académico.',
        'modalidad': Evento.ModalidadChoices.PRESENCIAL,
        'lugar': 'Auditorio Central',
        'fecha_inicio': str(date.today()),
        'fecha_fin': str(date.today() + timedelta(days=1)),
        'estado': Evento.EstadoChoices.ACTIVO,
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_admin_can_create_evento(auth_client, admin_user):
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(), format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
@pytest.mark.parametrize('role_fixture', [
    'director_grupo', 'director_semillero', 'lider_estudiantil', 'estudiante',
])
def test_non_admin_cannot_create_evento(auth_client, request, role_fixture):
    user = request.getfixturevalue(role_fixture)
    client = auth_client(user)
    resp = client.post(URL, _payload(), format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_evento_readable_by_non_admin(auth_client, estudiante):
    evento = _crear_evento()
    client = auth_client(estudiante)
    resp = client.get(URL)
    assert resp.status_code == 200
    ids = [e['id'] for e in resp.json()['results']]
    assert evento.id in ids


@pytest.mark.django_db
def test_admin_can_update_and_delete_evento(auth_client, admin_user):
    evento = _crear_evento()
    client = auth_client(admin_user)

    resp = client.patch(f'{URL}{evento.id}/', {'estado': Evento.EstadoChoices.FINALIZADO},
                        format='json')
    assert resp.status_code == 200, resp.content

    resp = client.delete(f'{URL}{evento.id}/')
    assert resp.status_code == 204
    assert not Evento.objects.filter(id=evento.id).exists()


@pytest.mark.django_db
def test_non_admin_cannot_delete_evento(auth_client, director_semillero):
    evento = _crear_evento()
    client = auth_client(director_semillero)
    resp = client.delete(f'{URL}{evento.id}/')
    assert resp.status_code == 403
    assert Evento.objects.filter(id=evento.id).exists()


@pytest.mark.django_db
def test_fecha_fin_anterior_a_inicio_es_invalida(auth_client, admin_user):
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(
        fecha_inicio=str(date.today()),
        fecha_fin=str(date.today() - timedelta(days=1)),
    ), format='json')
    assert resp.status_code == 400
    assert 'fecha_fin' in resp.json()
