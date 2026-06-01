"""Tests for /api/v1/core/postulaciones/ — RBAC, alcance, aval gate y resolución.

Reglas verificadas:
- Director de Semillero crea postulaciones de SU semillero (con aval aprobado,
  estudiantes matriculados y convocatoria abierta).
- Aval gate: no se postula un semillero sin aval aprobado.
- Estudiante no matriculado no puede incluirse.
- Resolución (aprobar/rechazar): solo Administrador y Director de Grupo.
- Filtro por filas por rol (get_queryset).
"""
from datetime import date, timedelta

import pytest

from apps.sigesi.models import (
    Convocatoria,
    Evento,
    MatriculaSemillero,
    Postulacion,
    Semillero,
)


URL = '/api/v1/core/postulaciones/'


def _crear_evento(nombre='Congreso de IA'):
    return Evento.objects.create(
        nombre=nombre,
        fecha_inicio=date.today(),
        fecha_fin=date.today() + timedelta(days=2),
    )


def _convocatoria(evento, estado=Convocatoria.EstadoChoices.ABIERTA):
    return Convocatoria.objects.create(
        evento=evento,
        titulo='Convocatoria de movilidad',
        descripcion='desc',
        tipo=Convocatoria.TipoChoices.INTERNA,
        fecha_apertura=date.today(),
        fecha_cierre=date.today() + timedelta(days=15),
        estado=estado,
    )


def _matricular(estudiante, semillero):
    return MatriculaSemillero.objects.create(
        estudiante=estudiante, semillero=semillero, semestre='2025-1')


def _postulacion(convocatoria, semillero, estudiantes=(),
                 estado=Postulacion.EstadoChoices.PENDIENTE):
    p = Postulacion.objects.create(
        convocatoria=convocatoria, semillero=semillero, estado=estado)
    if estudiantes:
        p.estudiantes.set(estudiantes)
    return p


def _payload(convocatoria, semillero, estudiantes):
    return {
        'convocatoria': convocatoria.id,
        'semillero': semillero.id,
        'estudiantes': [e.id for e in estudiantes],
    }


# ------------------------------------------------------- Director de Semillero

@pytest.mark.django_db
def test_director_semillero_crea_para_su_semillero(
    auth_client, director_semillero, estudiante, semillero_aprobado
):
    _matricular(estudiante, semillero_aprobado)
    evento = _crear_evento()
    convocatoria = _convocatoria(evento)
    client = auth_client(director_semillero)
    resp = client.post(
        URL, _payload(convocatoria, semillero_aprobado, [estudiante]),
        format='json')
    assert resp.status_code == 201, resp.content
    assert resp.json()['data']['estado'] == Postulacion.EstadoChoices.PENDIENTE


@pytest.mark.django_db
def test_director_semillero_no_postula_semillero_ajeno(
    auth_client, director_semillero, estudiante, grupo
):
    # Semillero aprobado pero NO dirigido por este director (director=None).
    ajeno = Semillero.objects.create(
        nombre='Semillero Ajeno', codigo='SX', objetivo='x',
        fecha_creacion=date.today(), grupo_investigacion=grupo, director=None,
        estado_aval=Semillero.EstadoAvalChoices.APROBADO,
    )
    evento = _crear_evento()
    convocatoria = _convocatoria(evento)
    client = auth_client(director_semillero)
    resp = client.post(
        URL, _payload(convocatoria, ajeno, [estudiante]), format='json')
    assert resp.status_code == 400
    assert 'semillero' in resp.json()


@pytest.mark.django_db
def test_aval_gate_bloquea_semillero_sin_aprobar(
    auth_client, director_semillero, estudiante, semillero_sin_aprobar
):
    _matricular(estudiante, semillero_sin_aprobar)
    evento = _crear_evento()
    convocatoria = _convocatoria(evento)
    client = auth_client(director_semillero)
    resp = client.post(
        URL, _payload(convocatoria, semillero_sin_aprobar, [estudiante]),
        format='json')
    assert resp.status_code == 400
    assert 'semillero' in resp.json()


@pytest.mark.django_db
def test_estudiante_no_matriculado_rechazado(
    auth_client, director_semillero, otro_estudiante, semillero_aprobado
):
    evento = _crear_evento()
    convocatoria = _convocatoria(evento)
    client = auth_client(director_semillero)
    resp = client.post(
        URL, _payload(convocatoria, semillero_aprobado, [otro_estudiante]),
        format='json')
    assert resp.status_code == 400
    assert 'estudiantes' in resp.json()


@pytest.mark.django_db
def test_convocatoria_cerrada_rechazada(
    auth_client, director_semillero, estudiante, semillero_aprobado
):
    _matricular(estudiante, semillero_aprobado)
    evento = _crear_evento()
    convocatoria = _convocatoria(
        evento, estado=Convocatoria.EstadoChoices.CERRADA)
    client = auth_client(director_semillero)
    resp = client.post(
        URL, _payload(convocatoria, semillero_aprobado, [estudiante]),
        format='json')
    assert resp.status_code == 400
    assert 'convocatoria' in resp.json()


# --------------------------------------------------------------- Lectura/403

@pytest.mark.django_db
def test_estudiante_no_puede_crear(
    auth_client, estudiante, semillero_aprobado
):
    evento = _crear_evento()
    convocatoria = _convocatoria(evento)
    client = auth_client(estudiante)
    resp = client.post(
        URL, _payload(convocatoria, semillero_aprobado, [estudiante]),
        format='json')
    assert resp.status_code == 403


# ----------------------------------------------------- Resolución (aprobar)

@pytest.mark.django_db
def test_director_grupo_aprueba(
    auth_client, director_grupo, semillero_aprobado
):
    evento = _crear_evento()
    convocatoria = _convocatoria(evento)
    postulacion = _postulacion(convocatoria, semillero_aprobado)
    client = auth_client(director_grupo)
    resp = client.post(f'{URL}{postulacion.id}/aprobar/', {}, format='json')
    assert resp.status_code == 200, resp.content
    postulacion.refresh_from_db()
    assert postulacion.estado == Postulacion.EstadoChoices.ACEPTADA
    assert postulacion.aprobado_por_id == director_grupo.id
    assert postulacion.fecha_resolucion is not None


@pytest.mark.django_db
def test_admin_aprueba(auth_client, admin_user, semillero_aprobado):
    evento = _crear_evento()
    convocatoria = _convocatoria(evento)
    postulacion = _postulacion(convocatoria, semillero_aprobado)
    client = auth_client(admin_user)
    resp = client.post(f'{URL}{postulacion.id}/aprobar/', {}, format='json')
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
def test_director_semillero_no_puede_aprobar(
    auth_client, director_semillero, semillero_aprobado
):
    evento = _crear_evento()
    convocatoria = _convocatoria(evento)
    postulacion = _postulacion(convocatoria, semillero_aprobado)
    client = auth_client(director_semillero)
    resp = client.post(f'{URL}{postulacion.id}/aprobar/', {}, format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_rechazar_marca_estado(
    auth_client, director_grupo, semillero_aprobado
):
    evento = _crear_evento()
    convocatoria = _convocatoria(evento)
    postulacion = _postulacion(convocatoria, semillero_aprobado)
    client = auth_client(director_grupo)
    resp = client.post(f'{URL}{postulacion.id}/rechazar/',
                       {'resultado': 'No cumple requisitos'}, format='json')
    assert resp.status_code == 200, resp.content
    postulacion.refresh_from_db()
    assert postulacion.estado == Postulacion.EstadoChoices.RECHAZADA


# ------------------------------------------------------------- Filtro por rol

@pytest.mark.django_db
def test_scope_filter_director_semillero(
    auth_client, director_semillero, semillero_aprobado, grupo
):
    evento = _crear_evento()
    convocatoria = _convocatoria(evento)
    propia = _postulacion(convocatoria, semillero_aprobado)

    ajeno = Semillero.objects.create(
        nombre='Semillero Ajeno', codigo='SX', objetivo='x',
        fecha_creacion=date.today(), grupo_investigacion=grupo, director=None,
        estado_aval=Semillero.EstadoAvalChoices.APROBADO,
    )
    ajena = _postulacion(convocatoria, ajeno)

    client = auth_client(director_semillero)
    resp = client.get(URL)
    assert resp.status_code == 200
    ids = [p['id'] for p in resp.json()['results']]
    assert propia.id in ids
    assert ajena.id not in ids
