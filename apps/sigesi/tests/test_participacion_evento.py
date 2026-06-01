"""Tests for /api/v1/core/participaciones-evento/ — RBAC, alcance, unicidad y carga de certificado.

Reglas verificadas:
- Administrador: CRUD total.
- Director de Grupo / Director de Semillero / Líder Estudiantil: pueden registrar
  participantes dentro de su alcance (estudiantes/líderes de su grupo/semillero;
  el líder, además, a sí mismo) y gestionarlos.
- Estudiante: solo lectura de sus propias participaciones.
- Unicidad: un participante una sola vez por evento.
- ``POST .../cargar-certificado/`` sube el certificado respetando el alcance.
"""
from datetime import date, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.sigesi.models import (
    Convocatoria,
    Evento,
    MatriculaSemillero,
    ParticipacionEvento,
    Postulacion,
)


URL = '/api/v1/core/participaciones-evento/'


def _crear_evento(nombre='Congreso de IA'):
    return Evento.objects.create(
        nombre=nombre,
        fecha_inicio=date.today(),
        fecha_fin=date.today() + timedelta(days=2),
    )


def _matricular(estudiante, semillero):
    return MatriculaSemillero.objects.create(
        estudiante=estudiante,
        semillero=semillero,
        semestre='2025-1',
    )


def _postulacion_aceptada(evento, semillero, estudiantes):
    """Crea (por ORM) una convocatoria del evento y una postulación aceptada.

    Habilita el gate de flujo de ParticipacionEvento para los ``estudiantes``
    indicados (se crea directamente, sin pasar por el serializer).
    """
    convocatoria = Convocatoria.objects.create(
        evento=evento,
        titulo='Convocatoria de prueba',
        descripcion='desc',
        tipo=Convocatoria.TipoChoices.INTERNA,
        fecha_apertura=date.today(),
        fecha_cierre=date.today() + timedelta(days=10),
        estado=Convocatoria.EstadoChoices.ABIERTA,
    )
    postulacion = Postulacion.objects.create(
        convocatoria=convocatoria,
        semillero=semillero,
        estado=Postulacion.EstadoChoices.ACEPTADA,
    )
    postulacion.estudiantes.set(estudiantes)
    return postulacion


def _crear_participacion(participante, evento, tipo='asistente'):
    return ParticipacionEvento.objects.create(
        participante=participante,
        evento=evento,
        tipo_participacion=tipo,
    )


def _payload(participante, evento, tipo='asistente'):
    return {
        'participante': participante.id,
        'evento': evento.id,
        'tipo_participacion': tipo,
    }


# --------------------------------------------------------------------- Admin

@pytest.mark.django_db
def test_admin_full_crud(auth_client, admin_user, estudiante):
    evento = _crear_evento()
    client = auth_client(admin_user)

    resp = client.post(URL, _payload(estudiante, evento), format='json')
    assert resp.status_code == 201, resp.content
    pid = resp.json()['data']['id']

    resp = client.patch(f'{URL}{pid}/', {'tipo_participacion': 'ponente'}, format='json')
    assert resp.status_code == 200, resp.content

    resp = client.delete(f'{URL}{pid}/')
    assert resp.status_code == 204
    assert not ParticipacionEvento.objects.filter(id=pid).exists()


# ------------------------------------------------------- Director de Semillero

@pytest.mark.django_db
def test_director_semillero_can_add_in_scope_student(
    auth_client, director_semillero, estudiante, semillero_aprobado
):
    _matricular(estudiante, semillero_aprobado)
    evento = _crear_evento()
    _postulacion_aceptada(evento, semillero_aprobado, [estudiante])
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(estudiante, evento), format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_director_semillero_rejected_for_out_of_scope_student(
    auth_client, director_semillero, otro_estudiante, semillero_aprobado
):
    # otro_estudiante NO está matriculado en el semillero del director.
    evento = _crear_evento()
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(otro_estudiante, evento), format='json')
    assert resp.status_code == 400
    assert 'participante' in resp.json()


# ----------------------------------------------------------- Director de Grupo

@pytest.mark.django_db
def test_director_grupo_can_add_student_of_group_semillero(
    auth_client, director_grupo, estudiante, semillero_aprobado
):
    _matricular(estudiante, semillero_aprobado)
    evento = _crear_evento()
    _postulacion_aceptada(evento, semillero_aprobado, [estudiante])
    client = auth_client(director_grupo)
    resp = client.post(URL, _payload(estudiante, evento), format='json')
    assert resp.status_code == 201, resp.content


# ------------------------------------------------------------- Líder Estudiantil

@pytest.mark.django_db
def test_lider_can_add_in_scope_student_and_self(
    auth_client, lider_estudiantil, estudiante, semillero_aprobado
):
    _matricular(estudiante, semillero_aprobado)
    evento = _crear_evento()
    _postulacion_aceptada(
        evento, semillero_aprobado, [estudiante, lider_estudiantil])
    client = auth_client(lider_estudiantil)

    resp = client.post(URL, _payload(estudiante, evento), format='json')
    assert resp.status_code == 201, resp.content

    # El líder puede registrarse a sí mismo (es líder del semillero y, por
    # invariante de User.save(), también estudiante).
    resp = client.post(URL, _payload(lider_estudiantil, evento), format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_lider_rejected_for_out_of_scope_student(
    auth_client, lider_estudiantil, otro_estudiante, semillero_aprobado
):
    evento = _crear_evento()
    client = auth_client(lider_estudiantil)
    resp = client.post(URL, _payload(otro_estudiante, evento), format='json')
    assert resp.status_code == 400


# ----------------------------------------------------------------- Estudiante

@pytest.mark.django_db
def test_estudiante_sees_only_own_participations(
    auth_client, estudiante, otro_estudiante
):
    evento = _crear_evento()
    propia = _crear_participacion(estudiante, evento)
    ajena = _crear_participacion(otro_estudiante, evento)
    client = auth_client(estudiante)

    resp = client.get(URL)
    assert resp.status_code == 200
    ids = [p['id'] for p in resp.json()['results']]
    assert propia.id in ids
    assert ajena.id not in ids


@pytest.mark.django_db
def test_estudiante_cannot_create(auth_client, estudiante):
    evento = _crear_evento()
    client = auth_client(estudiante)
    resp = client.post(URL, _payload(estudiante, evento), format='json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_estudiante_cannot_update_own(auth_client, estudiante):
    evento = _crear_evento()
    participacion = _crear_participacion(estudiante, evento)
    client = auth_client(estudiante)
    resp = client.patch(f'{URL}{participacion.id}/',
                        {'tipo_participacion': 'ponente'}, format='json')
    assert resp.status_code == 403


# --------------------------------------------------------- Reglas de negocio

@pytest.mark.django_db
def test_participante_unico_por_evento(auth_client, admin_user, estudiante):
    evento = _crear_evento()
    client = auth_client(admin_user)

    resp = client.post(URL, _payload(estudiante, evento), format='json')
    assert resp.status_code == 201, resp.content

    resp = client.post(URL, _payload(estudiante, evento), format='json')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_participante_debe_ser_estudiante_o_lider(
    auth_client, admin_user, director_grupo
):
    evento = _crear_evento()
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(director_grupo, evento), format='json')
    assert resp.status_code == 400
    assert 'participante' in resp.json()


@pytest.mark.django_db
def test_scope_filter_oculta_filas_fuera_de_alcance(
    auth_client, director_semillero, estudiante, otro_estudiante, semillero_aprobado
):
    _matricular(estudiante, semillero_aprobado)
    evento = _crear_evento()
    en_alcance = _crear_participacion(estudiante, evento)
    fuera_alcance = _crear_participacion(otro_estudiante, evento)

    client = auth_client(director_semillero)
    resp = client.get(URL)
    assert resp.status_code == 200
    ids = [p['id'] for p in resp.json()['results']]
    assert en_alcance.id in ids
    assert fuera_alcance.id not in ids


# ------------------------------------------------------- Cargar certificado

@pytest.mark.django_db
def test_cargar_certificado_in_scope(
    auth_client, director_semillero, estudiante, semillero_aprobado
):
    _matricular(estudiante, semillero_aprobado)
    evento = _crear_evento()
    participacion = _crear_participacion(estudiante, evento)
    client = auth_client(director_semillero)

    archivo = SimpleUploadedFile('cert.pdf', b'%PDF-1.4 contenido',
                                 content_type='application/pdf')
    resp = client.post(f'{URL}{participacion.id}/cargar-certificado/',
                       {'certificado': archivo}, format='multipart')
    assert resp.status_code == 200, resp.content
    assert resp.json()['certificado']
    participacion.refresh_from_db()
    assert participacion.certificado


@pytest.mark.django_db
def test_cargar_certificado_out_of_scope_404(
    auth_client, director_semillero, otro_estudiante, semillero_aprobado
):
    # Participación de un estudiante fuera del alcance del director: oculta por
    # get_queryset, así que get_object responde 404.
    evento = _crear_evento()
    participacion = _crear_participacion(otro_estudiante, evento)
    client = auth_client(director_semillero)

    archivo = SimpleUploadedFile('cert.pdf', b'%PDF-1.4', content_type='application/pdf')
    resp = client.post(f'{URL}{participacion.id}/cargar-certificado/',
                       {'certificado': archivo}, format='multipart')
    assert resp.status_code == 404


@pytest.mark.django_db
def test_cargar_certificado_extension_invalida_400(
    auth_client, director_semillero, estudiante, semillero_aprobado
):
    _matricular(estudiante, semillero_aprobado)
    evento = _crear_evento()
    participacion = _crear_participacion(estudiante, evento)
    client = auth_client(director_semillero)

    archivo = SimpleUploadedFile('cert.txt', b'texto plano', content_type='text/plain')
    resp = client.post(f'{URL}{participacion.id}/cargar-certificado/',
                       {'certificado': archivo}, format='multipart')
    assert resp.status_code == 400


# ----------------------------------------------------- Gate de flujo (postulación)

@pytest.mark.django_db
def test_gate_bloquea_sin_postulacion_aceptada(
    auth_client, director_semillero, estudiante, semillero_aprobado
):
    # Estudiante en alcance y matriculado, pero SIN postulación aceptada que
    # respalde la participación → el gate de flujo responde 400.
    _matricular(estudiante, semillero_aprobado)
    evento = _crear_evento()
    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(estudiante, evento), format='json')
    assert resp.status_code == 400
    assert 'participante' in resp.json()


@pytest.mark.django_db
def test_gate_postulacion_pendiente_no_habilita(
    auth_client, director_semillero, estudiante, semillero_aprobado
):
    # Existe postulación que incluye al estudiante, pero en estado pendiente:
    # no habilita la participación.
    _matricular(estudiante, semillero_aprobado)
    evento = _crear_evento()
    postulacion = _postulacion_aceptada(evento, semillero_aprobado, [estudiante])
    postulacion.estado = Postulacion.EstadoChoices.PENDIENTE
    postulacion.save(update_fields=['estado'])

    client = auth_client(director_semillero)
    resp = client.post(URL, _payload(estudiante, evento), format='json')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_admin_omite_gate_de_flujo(auth_client, admin_user, estudiante):
    # El administrador puede registrar participaciones sin postulación previa.
    evento = _crear_evento()
    client = auth_client(admin_user)
    resp = client.post(URL, _payload(estudiante, evento), format='json')
    assert resp.status_code == 201, resp.content
