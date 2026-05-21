"""Descarga de archivos vía el mixin ArchiveDownloadMixin: /{id}/archive/download/."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.sigesi.models import Evidencia, ProduccionAcademica

CRONO_URL = '/api/v1/core/cronograma-proyecto/'
AVANCES_URL = '/api/v1/core/avances/'
PROD_URL = '/api/v1/core/producciones-academicas/'


@pytest.fixture(autouse=True)
def _media_tmp(settings, tmp_path):
    """Aísla los archivos subidos en un directorio temporal por test."""
    settings.MEDIA_ROOT = str(tmp_path)


def _read(resp):
    return b"".join(resp.streaming_content)


# ---------------------------------------------------------------- cronograma

@pytest.mark.django_db
def test_download_cronograma_archivo(auth_client, admin_user, cronograma_row):
    cronograma_row.archivo_cronograma = SimpleUploadedFile(
        'crono.pdf', b'CRONO-BYTES', content_type='application/pdf')
    cronograma_row.save()

    client = auth_client(admin_user)
    resp = client.get(f'{CRONO_URL}{cronograma_row.id}/archive/download/')
    assert resp.status_code == 200
    assert resp.get('Content-Disposition', '').startswith('attachment;')
    assert _read(resp) == b'CRONO-BYTES'


@pytest.mark.django_db
def test_download_cronograma_sin_archivo_404(auth_client, admin_user, cronograma_row):
    client = auth_client(admin_user)
    resp = client.get(f'{CRONO_URL}{cronograma_row.id}/archive/download/')
    assert resp.status_code == 404


# ---------------------------------------------------------------- evidencia

@pytest.mark.django_db
def test_download_evidencia_archivo(auth_client, admin_user, actividad):
    ev = Evidencia.objects.create(
        actividad=actividad, tipo='documento', titulo='Evidencia',
        archivo=SimpleUploadedFile('ev.pdf', b'EVID-BYTES', content_type='application/pdf'),
        subido_por=admin_user,
    )
    client = auth_client(admin_user)
    resp = client.get(f'{AVANCES_URL}{ev.id}/archive/download/')
    assert resp.status_code == 200
    assert _read(resp) == b'EVID-BYTES'


# ---------------------------------------------------------------- producción (multi-archivo)

@pytest.mark.django_db
def test_download_produccion_default_y_certificado(auth_client, admin_user, semillero_aprobado, estudiante):
    pa = ProduccionAcademica.objects.create(
        titulo='Paper', tipo='articulo', semillero=semillero_aprobado,
        archivo=SimpleUploadedFile('a.pdf', b'ARCHIVO-BYTES', content_type='application/pdf'),
        certificado=SimpleUploadedFile('c.pdf', b'CERT-BYTES', content_type='application/pdf'),
    )
    pa.autores.set([estudiante])

    client = auth_client(admin_user)

    # Por defecto descarga el campo 'archivo'.
    resp = client.get(f'{PROD_URL}{pa.id}/archive/download/')
    assert resp.status_code == 200
    assert _read(resp) == b'ARCHIVO-BYTES'

    # ?field=certificado descarga el certificado.
    resp_cert = client.get(f'{PROD_URL}{pa.id}/archive/download/?field=certificado')
    assert resp_cert.status_code == 200
    assert _read(resp_cert) == b'CERT-BYTES'


@pytest.mark.django_db
def test_download_produccion_campo_invalido_400(auth_client, admin_user, semillero_aprobado, estudiante):
    pa = ProduccionAcademica.objects.create(
        titulo='Paper', tipo='articulo', semillero=semillero_aprobado,
        archivo=SimpleUploadedFile('a.pdf', b'X', content_type='application/pdf'),
    )
    pa.autores.set([estudiante])
    client = auth_client(admin_user)
    resp = client.get(f'{PROD_URL}{pa.id}/archive/download/?field=inexistente')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_download_produccion_sin_archivo_404(auth_client, admin_user, semillero_aprobado, estudiante):
    pa = ProduccionAcademica.objects.create(
        titulo='Sin archivo', tipo='articulo', semillero=semillero_aprobado)
    pa.autores.set([estudiante])
    client = auth_client(admin_user)
    resp = client.get(f'{PROD_URL}{pa.id}/archive/download/')
    assert resp.status_code == 404
