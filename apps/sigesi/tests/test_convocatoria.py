"""Tests for /api/v1/core/convocatorias/ — RBAC y vínculo con el evento.

Reglas verificadas:
- Administrador y Director de Grupo: CRUD completo.
- Director de Semillero / Líder Estudiantil / Estudiante: solo lectura (403 al escribir).
- Toda convocatoria debe referirse a un evento.
"""
from datetime import date, timedelta

import pytest

from apps.sigesi.models import Convocatoria, Evento


URL = '/api/v1/core/convocatorias/'


def _crear_evento(nombre='Congreso de IA'):
    return Evento.objects.create(
        nombre=nombre,
        fecha_inicio=date.today(),
        fecha_fin=date.today() + timedelta(days=2),
    )


def _payload(evento, **overrides):
    data = {
        'evento': evento.id,
        'titulo': 'Convocatoria de movilidad',
        'descripcion': 'Apoyo a la asistencia a eventos.',
        'tipo': Convocatoria.TipoChoices.INTERNA,
        'fecha_apertura': str(date.today()),
        'fecha_cierre': str(date.today() + timedelta(days=15)),
    }
    data.update(overrides)
    return data


# --------------------------------------------------------------- Escritura OK

@pytest.mark.django_db
def test_admin_puede_crear(auth_client, admin_user):
    evento = _crear_evento()
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(evento), format='json')
    assert resp.status_code == 201, resp.content
    assert resp.json()['data']['evento']['id'] == evento.id


@pytest.mark.django_db
def test_director_grupo_puede_crear(auth_client, director_grupo):
    evento = _crear_evento()
    client = auth_client(director_grupo)
    resp = client.post(URL, _payload(evento), format='json')
    assert resp.status_code == 201, resp.content


# ------------------------------------------------------------ Escritura 403

@pytest.mark.django_db
def test_director_semillero_no_puede_crear(auth_client, director_semillero):
    evento = _crear_evento()
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(evento), format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_estudiante_no_puede_crear(auth_client, estudiante):
    evento = _crear_evento()
    client = auth_client(estudiante)
    resp = client.post(URL, _payload(evento), format='json')
    assert resp.status_code == 403


# ---------------------------------------------------------------- Lectura OK

@pytest.mark.django_db
def test_estudiante_puede_leer(auth_client, estudiante):
    evento = _crear_evento()
    Convocatoria.objects.create(
        evento=evento, titulo='C1', descripcion='d',
        tipo=Convocatoria.TipoChoices.INTERNA,
        fecha_apertura=date.today(),
        fecha_cierre=date.today() + timedelta(days=5),
    )
    client = auth_client(estudiante)
    resp = client.get(URL)
    assert resp.status_code == 200
    assert resp.json()['count'] == 1


# --------------------------------------------------------- Reglas de negocio

@pytest.mark.django_db
def test_evento_requerido(auth_client, admin_user):
    client = auth_client(admin_user)
    payload = {
        'titulo': 'Sin evento',
        'descripcion': 'x',
        'tipo': Convocatoria.TipoChoices.INTERNA,
        'fecha_apertura': str(date.today()),
        'fecha_cierre': str(date.today() + timedelta(days=5)),
    }
    resp = client.post(URL, payload, format='json')
    assert resp.status_code == 400
    assert 'evento' in resp.json()


@pytest.mark.django_db
def test_fecha_cierre_no_anterior_a_apertura(auth_client, admin_user):
    evento = _crear_evento()
    client = auth_client(admin_user)
    payload = _payload(
        evento,
        fecha_apertura=str(date.today()),
        fecha_cierre=str(date.today() - timedelta(days=1)),
    )
    resp = client.post(URL, payload, format='json')
    assert resp.status_code == 400
    assert 'fecha_cierre' in resp.json()
