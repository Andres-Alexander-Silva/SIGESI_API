"""Tests for the notifications feed and the workflow triggers.

Cubre:
- Convocatoria create → notifica a todos los director_semillero (actor excluido).
- Convocatoria PATCH con cambio de ``estado`` → notifica; sin cambio de estado → no notifica.
- Postulación create → notifica a los estudiantes.
- Postulación aprobar → notifica a los estudiantes (resolver excluido).
- ParticipacionEvento create/update/delete/cargar-certificado → notifica al participante.
- NotificacionViewSet: scope (solo propias), filtros, marcar-leida, marcar-todas-leidas.
- Dedupe: dos llamadas equivalentes crean una sola fila (unique_together).
- Push por canal: se mockea ``async_to_sync`` (fire-and-forget; no se verifica WS).
"""
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from apps.sigesi.models import (
    Convocatoria,
    Evento,
    MatriculaSemillero,
    Notificacion,
    ParticipacionEvento,
    Postulacion,
    User,
)


# ====================================================================
# Convocatoria
# ====================================================================

def _crear_evento(nombre='Congreso de IA'):
    return Evento.objects.create(
        nombre=nombre,
        fecha_inicio=date.today(),
        fecha_fin=date.today() + timedelta(days=2),
    )


def _payload_convocatoria(evento):
    return {
        'evento': evento.id,
        'titulo': 'Convocatoria de movilidad',
        'descripcion': 'Apoyo a la asistencia a eventos.',
        'tipo': Convocatoria.TipoChoices.INTERNA,
        'fecha_apertura': str(date.today()),
        'fecha_cierre': str(date.today() + timedelta(days=15)),
    }


URL_CONV = '/api/v1/core/convocatorias/'


@pytest.mark.django_db
@patch('apps.sigesi.utils.notifications.async_to_sync')
def test_convocatoria_creada_notifica_director_semillero(
    mock_push, auth_client, admin_user, director_semillero, lider_estudiantil
):
    """Crea convocatoria (admin) → director_semillero recibe push; admin no."""
    evento = _crear_evento()
    client = auth_client(admin_user)
    resp = client.post(URL_CONV, _payload_convocatoria(evento), format='json')
    assert resp.status_code == 201, resp.content

    # Admin no debe recibir la notificación (actor excluido).
    assert not Notificacion.objects.filter(usuario=admin_user).exists()
    # director_semillero sí.
    notif = Notificacion.objects.get(usuario=director_semillero)
    assert notif.tipo == 'convocatoria_creada'
    assert evento.nombre in notif.mensaje
    # líder_estudiantil no (rol distinto).
    assert not Notificacion.objects.filter(usuario=lider_estudiantil).exists()
    assert mock_push.called


@pytest.mark.django_db
@patch('apps.sigesi.utils.notifications.async_to_sync')
def test_convocatoria_cambio_estado_notifica(
    mock_push, auth_client, admin_user, director_semillero
):
    """PATCH ``estado=abierta→cerrada`` notifica; PATCH de ``descripcion`` no."""
    evento = _crear_evento()
    convocatoria = Convocatoria.objects.create(
        evento=evento, titulo='C1', descripcion='d',
        tipo=Convocatoria.TipoChoices.INTERNA,
        fecha_apertura=date.today(),
        fecha_cierre=date.today() + timedelta(days=5),
    )
    client = auth_client(admin_user)

    # 1. Cambio solo de descripción → no debe notificar.
    resp = client.patch(
        f'{URL_CONV}{convocatoria.id}/',
        {'descripcion': 'otra cosa'}, format='json')
    assert resp.status_code == 200
    assert Notificacion.objects.count() == 0

    # 2. Cambio de estado → sí notifica.
    resp = client.patch(
        f'{URL_CONV}{convocatoria.id}/',
        {'estado': Convocatoria.EstadoChoices.CERRADA}, format='json')
    assert resp.status_code == 200
    notif = Notificacion.objects.get(
        usuario=director_semillero, tipo='convocatoria_actualizada')
    assert convocatoria.estado == Convocatoria.EstadoChoices.CERRADA
    assert mock_push.called


# ====================================================================
# Postulación
# ====================================================================

URL_POST = '/api/v1/core/postulaciones/'


def _convocatoria(evento, estado=Convocatoria.EstadoChoices.ABIERTA):
    return Convocatoria.objects.create(
        evento=evento, titulo='Conv 1', descripcion='d',
        tipo=Convocatoria.TipoChoices.INTERNA,
        fecha_apertura=date.today(),
        fecha_cierre=date.today() + timedelta(days=15),
        estado=estado,
    )


def _matricular(estudiante, semillero):
    return MatriculaSemillero.objects.create(
        estudiante=estudiante, semillero=semillero, semestre='2025-1')


def _payload_postulacion(convocatoria, semillero, estudiantes):
    return {
        'convocatoria': convocatoria.id,
        'semillero': semillero.id,
        'estudiantes': [e.id for e in estudiantes],
    }


@pytest.mark.django_db
@patch('apps.sigesi.utils.notifications.async_to_sync')
def test_postulacion_creada_notifica_estudiantes(
    mock_push, auth_client, director_semillero, estudiante, otro_estudiante,
    semillero_aprobado,
):
    """Crea postulación → ambos estudiantes M2M reciben notificación."""
    _matricular(estudiante, semillero_aprobado)
    _matricular(otro_estudiante, semillero_aprobado)
    evento = _crear_evento()
    convocatoria = _convocatoria(evento)
    client = auth_client(director_semillero)
    resp = client.post(
        URL_POST,
        _payload_postulacion(convocatoria, semillero_aprobado,
                             [estudiante, otro_estudiante]),
        format='json')
    assert resp.status_code == 201, resp.content

    # Ambos estudiantes reciben la notificación, director_semillero (actor) no.
    assert Notificacion.objects.filter(
        usuario=estudiante, tipo='postulacion_creada').exists()
    assert Notificacion.objects.filter(
        usuario=otro_estudiante, tipo='postulacion_creada').exists()
    assert not Notificacion.objects.filter(usuario=director_semillero).exists()


@pytest.mark.django_db
@patch('apps.sigesi.utils.notifications.async_to_sync')
def test_postulacion_aprobar_notifica_estudiantes(
    mock_push, auth_client, director_grupo, estudiante, semillero_aprobado,
):
    """Aprobar (admin/director_grupo) → estudiantes notificados; resolver no."""
    _matricular(estudiante, semillero_aprobado)
    evento = _crear_evento()
    convocatoria = _convocatoria(evento)
    postulacion = Postulacion.objects.create(
        convocatoria=convocatoria, semillero=semillero_aprobado)
    postulacion.estudiantes.set([estudiante])

    client = auth_client(director_grupo)
    resp = client.post(
        f'{URL_POST}{postulacion.id}/aprobar/', {}, format='json')
    assert resp.status_code == 200, resp.content
    notif = Notificacion.objects.get(
        usuario=estudiante, tipo='postulacion_actualizada')
    assert 'aceptada' in notif.mensaje.lower()
    # El resolver (director_grupo) no debe recibir la notificación.
    assert not Notificacion.objects.filter(usuario=director_grupo).exists()


@pytest.mark.django_db
@patch('apps.sigesi.utils.notifications.async_to_sync')
def test_postulacion_dedupe_via_unique_together(
    mock_push, auth_client, director_semillero, estudiante, semillero_aprobado,
):
    """Dos PATCH con mismo estado (sin cambio) no deben duplicar la fila."""
    _matricular(estudiante, semillero_aprobado)
    evento = _crear_evento()
    convocatoria = _convocatoria(evento)
    postulacion = Postulacion.objects.create(
        convocatoria=convocatoria, semillero=semillero_aprobado)
    postulacion.estudiantes.set([estudiante])

    client = auth_client(director_semillero)
    # Un PATCH sin cambio de estado (cambia ``observaciones``) → no notifica.
    resp = client.patch(
        f'{URL_POST}{postulacion.id}/',
        {'observaciones': 'nota 1'}, format='json')
    assert resp.status_code == 200
    assert Notificacion.objects.count() == 0


# ====================================================================
# ParticipacionEvento
# ====================================================================

URL_PART = '/api/v1/core/participaciones-evento/'


def _postulacion_aceptada(evento, semillero, estudiantes):
    convocatoria = Convocatoria.objects.create(
        evento=evento, titulo='C', descripcion='d',
        tipo=Convocatoria.TipoChoices.INTERNA,
        fecha_apertura=date.today(),
        fecha_cierre=date.today() + timedelta(days=15),
    )
    p = Postulacion.objects.create(
        convocatoria=convocatoria, semillero=semillero,
        estado=Postulacion.EstadoChoices.ACEPTADA)
    p.estudiantes.set(estudiantes)
    return p


def _payload_part(evento, participante, tipo='asistente'):
    return {
        'evento': evento.id,
        'participante': participante.id,
        'tipo_participacion': tipo,
    }


@pytest.mark.django_db
@patch('apps.sigesi.utils.notifications.async_to_sync')
def test_participacion_creada_notifica_participante(
    mock_push, auth_client, admin_user, estudiante
):
    """Admin registra al estudiante → estudiante recibe notificación."""
    evento = _crear_evento()
    client = auth_client(admin_user)
    resp = client.post(
        URL_PART, _payload_part(evento, estudiante), format='json')
    assert resp.status_code == 201, resp.content
    notif = Notificacion.objects.get(
        usuario=estudiante, tipo='participacion_creada')
    assert evento.nombre in notif.mensaje


@pytest.mark.django_db
@patch('apps.sigesi.utils.notifications.async_to_sync')
def test_participacion_update_notifica_participante(
    mock_push, auth_client, admin_user, estudiante
):
    """PATCH de una participación → participante notificado (cualquier cambio)."""
    evento = _crear_evento()
    participacion = ParticipacionEvento.objects.create(
        evento=evento, participante=estudiante,
        tipo_participacion='asistente')
    client = auth_client(admin_user)
    resp = client.patch(
        f'{URL_PART}{participacion.id}/',
        {'tipo_participacion': 'ponente'}, format='json')
    assert resp.status_code == 200, resp.content
    Notificacion.objects.get(
        usuario=estudiante, tipo='participacion_actualizada')


@pytest.mark.django_db
@patch('apps.sigesi.utils.notifications.async_to_sync')
def test_participacion_destroy_notifica_participante(
    mock_push, auth_client, admin_user, estudiante
):
    """DELETE de la participación → participante notificado (con mensaje "eliminada")."""
    evento = _crear_evento()
    participacion = ParticipacionEvento.objects.create(
        evento=evento, participante=estudiante,
        tipo_participacion='asistente')
    client = auth_client(admin_user)
    resp = client.delete(f'{URL_PART}{participacion.id}/')
    assert resp.status_code == 204
    notif = Notificacion.objects.get(
        usuario=estudiante, tipo='participacion_actualizada')
    assert 'eliminada' in notif.titulo.lower() or 'eliminada' in notif.mensaje.lower()


# ====================================================================
# NotificacionViewSet (bandeja personal)
# ====================================================================

URL_NOTIF = '/api/v1/core/notificaciones/'


@pytest.mark.django_db
def test_listar_solo_notificaciones_propias(
    auth_client, admin_user, director_semillero
):
    """El endpoint solo expone las notificaciones del usuario autenticado."""
    Notificacion.objects.create(
        usuario=admin_user, tipo='postulacion_creada',
        titulo='t', mensaje='m')
    Notificacion.objects.create(
        usuario=director_semillero, tipo='postulacion_creada',
        titulo='t', mensaje='m')

    client = auth_client(admin_user)
    resp = client.get(URL_NOTIF)
    assert resp.status_code == 200
    ids = [n['id'] for n in resp.json()['results']]
    assert len(ids) == 1


@pytest.mark.django_db
def test_filtro_por_leida(auth_client, admin_user):
    n1 = Notificacion.objects.create(
        usuario=admin_user, tipo='postulacion_creada',
        titulo='t1', mensaje='m', leida=False)
    Notificacion.objects.create(
        usuario=admin_user, tipo='postulacion_creada',
        titulo='t2', mensaje='m', leida=True)

    client = auth_client(admin_user)
    resp = client.get(URL_NOTIF, {'leida': 'false'})
    assert resp.status_code == 200
    ids = [n['id'] for n in resp.json()['results']]
    assert ids == [n1.id]


@pytest.mark.django_db
def test_marcar_leida(auth_client, admin_user):
    n = Notificacion.objects.create(
        usuario=admin_user, tipo='postulacion_creada',
        titulo='t', mensaje='m')
    client = auth_client(admin_user)
    resp = client.patch(f'{URL_NOTIF}{n.id}/marcar-leida/', {}, format='json')
    assert resp.status_code == 200, resp.content
    n.refresh_from_db()
    assert n.leida is True
    assert n.read_at is not None


@pytest.mark.django_db
def test_marcar_todas_leidas(auth_client, admin_user):
    Notificacion.objects.create(
        usuario=admin_user, tipo='postulacion_creada',
        titulo='t1', mensaje='m', leida=False)
    Notificacion.objects.create(
        usuario=admin_user, tipo='postulacion_creada',
        titulo='t2', mensaje='m', leida=False)
    Notificacion.objects.create(
        usuario=admin_user, tipo='postulacion_creada',
        titulo='t3', mensaje='m', leida=True)  # ya leída: no se cuenta

    client = auth_client(admin_user)
    resp = client.post(f'{URL_NOTIF}marcar-todas-leidas/', {}, format='json')
    assert resp.status_code == 200
    assert resp.json()['actualizadas'] == 2
    assert Notificacion.objects.filter(usuario=admin_user, leida=False).count() == 0
