"""Subida de archivos vía ArchiveUploadMixin: PATCH /{id}/archive/upload/."""
from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.sigesi.models import (
    CronogramaProyecto, Evidencia, ProduccionAcademica, Proyecto,
)

CRONO_URL = '/api/v1/core/cronograma-proyecto/'
AVANCES_URL = '/api/v1/core/avances/'
PROD_URL = '/api/v1/core/producciones-academicas/'


@pytest.fixture(autouse=True)
def _media_tmp(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def _pdf(name='doc.pdf', data=b'PDF-BYTES'):
    return SimpleUploadedFile(name, data, content_type='application/pdf')


# ---------------------------------------------------------------- cronograma

@pytest.mark.django_db
def test_upload_cronograma_archivo(auth_client, admin_user, cronograma_row):
    client = auth_client(admin_user)
    resp = client.patch(
        f'{CRONO_URL}{cronograma_row.id}/archive/upload/',
        {'file': _pdf(data=b'CRONO')}, format='multipart')
    assert resp.status_code == 200, resp.content
    cronograma_row.refresh_from_db()
    assert cronograma_row.archivo_cronograma
    # Y se puede descargar de vuelta.
    dl = client.get(f'{CRONO_URL}{cronograma_row.id}/archive/download/')
    assert b"".join(dl.streaming_content) == b'CRONO'


@pytest.mark.django_db
def test_upload_cronograma_aval_gate_blocks_non_admin(
    auth_client, director_semillero, semillero_sin_aprobar
):
    """El gate de aval (reusado del serializer) bloquea a un no-admin."""
    proyecto = Proyecto.objects.create(
        titulo='Sin aval', codigo='PSA1', descripcion='d', objetivo_general='o',
        director=director_semillero)
    proyecto.semilleros.set([semillero_sin_aprobar])
    crono = CronogramaProyecto.objects.create(
        proyecto=proyecto, actividad='A', descripcion_actividad='d',
        fecha_inicio=date.today(), fecha_fin=date.today(), fecha_entrega=date.today())

    client = auth_client(director_semillero)
    resp = client.patch(
        f'{CRONO_URL}{crono.id}/archive/upload/', {'file': _pdf()}, format='multipart')
    assert resp.status_code == 400
    assert 'aval aprobado' in resp.content.decode().lower()


@pytest.mark.django_db
def test_upload_no_file_returns_400(auth_client, admin_user, cronograma_row):
    client = auth_client(admin_user)
    resp = client.patch(f'{CRONO_URL}{cronograma_row.id}/archive/upload/', {}, format='multipart')
    assert resp.status_code == 400


# ---------------------------------------------------------------- evidencia

def _evidencia(actividad, user):
    return Evidencia.objects.create(
        actividad=actividad, tipo='documento', titulo='Ev',
        descripcion='desc', archivo=_pdf(name='orig.pdf', data=b'ORIG'),
        subido_por=user)


@pytest.mark.django_db
def test_upload_evidencia_valid(auth_client, admin_user, actividad):
    ev = _evidencia(actividad, admin_user)
    client = auth_client(admin_user)
    resp = client.patch(
        f'{AVANCES_URL}{ev.id}/archive/upload/',
        {'file': _pdf(name='nuevo.pdf', data=b'NUEVO')}, format='multipart')
    assert resp.status_code == 200, resp.content
    dl = client.get(f'{AVANCES_URL}{ev.id}/archive/download/')
    assert b"".join(dl.streaming_content) == b'NUEVO'


@pytest.mark.django_db
def test_upload_evidencia_invalid_extension(auth_client, admin_user, actividad):
    ev = _evidencia(actividad, admin_user)
    client = auth_client(admin_user)
    bad = SimpleUploadedFile('malo.exe', b'x', content_type='application/octet-stream')
    resp = client.patch(f'{AVANCES_URL}{ev.id}/archive/upload/', {'file': bad}, format='multipart')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_upload_evidencia_too_large(auth_client, admin_user, actividad):
    ev = _evidencia(actividad, admin_user)
    client = auth_client(admin_user)
    big = SimpleUploadedFile('big.pdf', b'x' * (6 * 1024 * 1024), content_type='application/pdf')
    resp = client.patch(f'{AVANCES_URL}{ev.id}/archive/upload/', {'file': big}, format='multipart')
    assert resp.status_code == 400


# ---------------------------------------------------------------- producción (multi-archivo)

@pytest.mark.django_db
def test_upload_produccion_default_and_certificado(
    auth_client, admin_user, semillero_aprobado, estudiante
):
    pa = ProduccionAcademica.objects.create(
        titulo='Paper', tipo='articulo', semillero=semillero_aprobado)
    pa.autores.set([estudiante])
    client = auth_client(admin_user)

    r1 = client.patch(
        f'{PROD_URL}{pa.id}/archive/upload/', {'file': _pdf(data=b'ARCH')}, format='multipart')
    assert r1.status_code == 200, r1.content

    r2 = client.patch(
        f'{PROD_URL}{pa.id}/archive/upload/?field=certificado',
        {'file': _pdf(data=b'CERT')}, format='multipart')
    assert r2.status_code == 200, r2.content

    pa.refresh_from_db()
    assert pa.archivo and pa.certificado
    assert b"".join(
        client.get(f'{PROD_URL}{pa.id}/archive/download/?field=certificado').streaming_content
    ) == b'CERT'


@pytest.mark.django_db
def test_upload_produccion_invalid_field_returns_400(
    auth_client, admin_user, semillero_aprobado, estudiante
):
    pa = ProduccionAcademica.objects.create(
        titulo='Paper', tipo='articulo', semillero=semillero_aprobado)
    pa.autores.set([estudiante])
    client = auth_client(admin_user)
    resp = client.patch(
        f'{PROD_URL}{pa.id}/archive/upload/?field=inexistente',
        {'file': _pdf()}, format='multipart')
    assert resp.status_code == 400
