"""Tests del ciclo de vida del almacenamiento (HU-021, fase F3).

Antes de esta fase, eliminar un registro con archivo lo dejaba huérfano en
MEDIA_ROOT para siempre — ver docs/HU-021_PLAN_IMPLEMENTACION.md, hallazgo
H3. django-cleanup (INSTALLED_APPS en settings.py) borra el archivo físico
en `post_delete` y al reemplazar el campo en `pre_save`.

Todas las pruebas fuerzan `MEDIA_ROOT` a un directorio temporal (fixture
`tmp_path`) para no escribir ni borrar nada dentro de `media/` del repo.

django-cleanup difiere el borrado físico a ``transaction.on_commit()`` (así
no borra el archivo si la transacción se revierte). El wrapping por defecto
de ``@pytest.mark.django_db`` envuelve cada test en una transacción que se
revierte al final, por lo que ese callback nunca se dispara: las pruebas que
verifican el borrado real usan ``django_db(transaction=True)``.
"""
import os
from datetime import date, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from apps.sigesi.models import (
    CronogramaProyecto,
    Evento,
    Evidencia,
    ParticipacionEvento,
    ProduccionAcademica,
)


def _pdf(name='archivo.pdf', content=b'%PDF-1.4 contenido'):
    return SimpleUploadedFile(name, content, content_type='application/pdf')


# ---------------------------------------------------------------------------
# T3.1 — el archivo se borra del disco al eliminar el registro
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_borrar_evidencia_borra_su_archivo_del_disco(actividad, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    ev = Evidencia.objects.create(
        actividad=actividad, tipo='documento', titulo='t', descripcion='d',
        archivo=_pdf(),
    )
    ruta = ev.archivo.path
    assert os.path.exists(ruta)

    ev.delete()

    assert not os.path.exists(ruta)


@pytest.mark.django_db(transaction=True)
def test_borrar_produccion_academica_borra_archivo_y_certificado(
    proyecto, semillero_aprobado, lider_estudiantil, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    pa = ProduccionAcademica.objects.create(
        titulo='Paper', tipo='articulo', descripcion='d',
        proyecto=proyecto, semillero=semillero_aprobado,
        archivo=_pdf('a.pdf'), certificado=_pdf('c.pdf'),
    )
    pa.autores.add(lider_estudiantil)
    ruta_archivo = pa.archivo.path
    ruta_certificado = pa.certificado.path
    assert os.path.exists(ruta_archivo)
    assert os.path.exists(ruta_certificado)

    pa.delete()

    assert not os.path.exists(ruta_archivo)
    assert not os.path.exists(ruta_certificado)


@pytest.mark.django_db(transaction=True)
def test_borrar_participacion_evento_borra_certificado(estudiante, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    evento = Evento.objects.create(
        nombre='Congreso', fecha_inicio=date.today(),
        fecha_fin=date.today() + timedelta(days=1),
    )
    part = ParticipacionEvento.objects.create(
        participante=estudiante, evento=evento, tipo_participacion='asistente',
        certificado=_pdf('cert.pdf'),
    )
    ruta = part.certificado.path
    assert os.path.exists(ruta)

    part.delete()

    assert not os.path.exists(ruta)


@pytest.mark.django_db(transaction=True)
def test_borrar_cronograma_proyecto_borra_su_archivo(proyecto, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    fila = CronogramaProyecto.objects.create(
        proyecto=proyecto, actividad='Diseño', descripcion_actividad='d',
        fecha_inicio=date.today(), fecha_fin=date.today(), fecha_entrega=date.today(),
        archivo_cronograma=_pdf(),
    )
    ruta = fila.archivo_cronograma.path
    assert os.path.exists(ruta)

    fila.delete()

    assert not os.path.exists(ruta)


# ---------------------------------------------------------------------------
# T3.2 — reemplazar el archivo borra el anterior (regresión de la limpieza
# manual retirada de ArchiveUploadMixin / semillero_view / participacion_evento_view)
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_reemplazar_evidencia_borra_el_archivo_anterior(
    auth_client, lider_estudiantil, actividad, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    ev = Evidencia.objects.create(
        actividad=actividad, tipo='documento', titulo='t', descripcion='d',
        archivo=_pdf('viejo.pdf'), subido_por=lider_estudiantil,
    )
    ruta_vieja = ev.archivo.path
    assert os.path.exists(ruta_vieja)

    client = auth_client(lider_estudiantil)
    resp = client.patch(
        f'/api/v1/core/avances/{ev.id}/archive/upload/',
        {'file': _pdf('nuevo.pdf')},
        format='multipart',
    )
    assert resp.status_code == 200, resp.content

    assert not os.path.exists(ruta_vieja)
    ev.refresh_from_db()
    assert os.path.exists(ev.archivo.path)


@pytest.mark.django_db(transaction=True)
def test_reemplazar_certificado_participacion_borra_el_anterior(
    auth_client, admin_user, estudiante, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    evento = Evento.objects.create(
        nombre='Congreso', fecha_inicio=date.today(),
        fecha_fin=date.today() + timedelta(days=1),
    )
    part = ParticipacionEvento.objects.create(
        participante=estudiante, evento=evento, tipo_participacion='asistente',
        certificado=_pdf('viejo.pdf'),
    )
    ruta_vieja = part.certificado.path
    assert os.path.exists(ruta_vieja)

    client = auth_client(admin_user)
    resp = client.post(
        f'/api/v1/core/participaciones-evento/{part.id}/cargar-certificado/',
        {'certificado': _pdf('nuevo.pdf')},
        format='multipart',
    )
    assert resp.status_code == 200, resp.content

    assert not os.path.exists(ruta_vieja)
    part.refresh_from_db()
    assert os.path.exists(part.certificado.path)


@pytest.mark.django_db(transaction=True)
def test_reemplazar_archivo_aval_borra_el_anterior(
    auth_client, admin_user, semillero_sin_aprobar, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    semillero_sin_aprobar.archivo_aval = _pdf('viejo.pdf')
    semillero_sin_aprobar.save()
    ruta_vieja = semillero_sin_aprobar.archivo_aval.path
    assert os.path.exists(ruta_vieja)

    client = auth_client(admin_user)
    resp = client.patch(
        f'/api/v1/core/semilleros/{semillero_sin_aprobar.id}/aval/',
        {'archivo_aval': _pdf('nuevo.pdf')},
        format='multipart',
    )
    assert resp.status_code == 200, resp.content

    assert not os.path.exists(ruta_vieja)
    semillero_sin_aprobar.refresh_from_db()
    assert os.path.exists(semillero_sin_aprobar.archivo_aval.path)


# ---------------------------------------------------------------------------
# T3.3 — limpiar_huerfanos
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_limpiar_huerfanos_dry_run_reporta_sin_borrar(settings, tmp_path, capsys):
    settings.MEDIA_ROOT = str(tmp_path)
    huerfano = tmp_path / 'evidencias' / '2026' / '01'
    huerfano.mkdir(parents=True)
    ruta = huerfano / 'suelto.pdf'
    ruta.write_bytes(b'%PDF-1.4')

    call_command('limpiar_huerfanos', '--dry-run')

    assert ruta.exists()
    salida = capsys.readouterr().out
    assert 'suelto.pdf' in salida
    assert 'no se elimin' in salida.lower()


@pytest.mark.django_db
def test_limpiar_huerfanos_sin_dry_run_elimina(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    huerfano = tmp_path / 'evidencias' / '2026' / '01'
    huerfano.mkdir(parents=True)
    ruta = huerfano / 'suelto.pdf'
    ruta.write_bytes(b'%PDF-1.4')

    call_command('limpiar_huerfanos')

    assert not ruta.exists()


@pytest.mark.django_db
def test_limpiar_huerfanos_no_borra_archivos_referenciados(actividad, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    ev = Evidencia.objects.create(
        actividad=actividad, tipo='documento', titulo='t', descripcion='d',
        archivo=_pdf(),
    )
    ruta = ev.archivo.path

    call_command('limpiar_huerfanos')

    assert os.path.exists(ruta)
