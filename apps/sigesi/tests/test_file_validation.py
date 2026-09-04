"""Tests de la unificación de validación de archivos (HU-021, fase F2).

Antes de esta fase, `validate_upload_file` (apps/sigesi/utils/download.py)
solo se aplicaba en la acción `archive/upload` de los mixins; el `POST`/`PUT`
directo de varios recursos (producción académica, cronograma de proyecto,
informes, foto de usuario, logo de semillero) no validaba nada — cualquier
extensión y cualquier tamaño pasaban. Ver docs/HU-021_PLAN_IMPLEMENTACION.md,
hallazgo H2.
"""
from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.sigesi.utils.download import validate_upload_file
from rest_framework import serializers


def _file(name, size_bytes=10, content_type='application/pdf'):
    return SimpleUploadedFile(name, b'x' * size_bytes, content_type=content_type)


# ---------------------------------------------------------------------------
# T2.1 — validate_upload_file (unitario)
# ---------------------------------------------------------------------------

def test_validate_upload_file_acepta_extension_permitida():
    validate_upload_file(_file('a.pdf'))  # no lanza


def test_validate_upload_file_rechaza_extension_no_permitida():
    with pytest.raises(serializers.ValidationError):
        validate_upload_file(_file('a.exe'))


def test_validate_upload_file_acepta_en_el_limite_exacto():
    validate_upload_file(_file('a.pdf', size_bytes=20 * 1024 * 1024))  # no lanza


def test_validate_upload_file_rechaza_un_byte_sobre_el_limite():
    with pytest.raises(serializers.ValidationError):
        validate_upload_file(_file('a.pdf', size_bytes=20 * 1024 * 1024 + 1))


def test_validate_upload_file_respeta_whitelist_restringida():
    validate_upload_file(_file('a.pdf'), extensiones={'.pdf'})  # no lanza
    with pytest.raises(serializers.ValidationError):
        validate_upload_file(_file('a.docx'), extensiones={'.pdf'})


# ---------------------------------------------------------------------------
# T2.2 / T2.3 — rutas que antes no validaban nada (regresión de H2)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_produccion_academica_rechaza_extension_no_permitida(
    auth_client, admin_user, proyecto, semillero_aprobado, lider_estudiantil, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    client = auth_client(admin_user)
    resp = client.post('/api/v1/core/producciones-academicas/', {
        'titulo': 'Paper', 'tipo': 'articulo', 'descripcion': 'desc',
        'proyecto': proyecto.id, 'semillero': semillero_aprobado.id,
        'autores': [lider_estudiantil.id], 'estado': 'en_elaboracion',
        'archivo': SimpleUploadedFile('malware.exe', b'MZ', content_type='application/octet-stream'),
    }, format='multipart')
    assert resp.status_code == 400
    assert 'archivo' in resp.json()


@pytest.mark.django_db
def test_produccion_academica_rechaza_certificado_sobredimensionado(
    auth_client, admin_user, proyecto, semillero_aprobado, lider_estudiantil, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    client = auth_client(admin_user)
    grande = b'a' * (20 * 1024 * 1024 + 1024)
    resp = client.post('/api/v1/core/producciones-academicas/', {
        'titulo': 'Paper', 'tipo': 'articulo', 'descripcion': 'desc',
        'proyecto': proyecto.id, 'semillero': semillero_aprobado.id,
        'autores': [lider_estudiantil.id], 'estado': 'en_elaboracion',
        'certificado': SimpleUploadedFile('c.pdf', grande, content_type='application/pdf'),
    }, format='multipart')
    assert resp.status_code == 400
    assert 'certificado' in resp.json()


@pytest.mark.django_db
def test_cronograma_proyecto_rechaza_extension_no_permitida(
    auth_client, director_semillero, proyecto, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    client = auth_client(director_semillero)
    resp = client.post('/api/v1/core/cronograma-proyecto/', {
        'proyecto': proyecto.id,
        'actividad': 'Diseño', 'descripcion_actividad': 'desc',
        'fecha_inicio': str(date.today()), 'fecha_fin': str(date.today()),
        'fecha_entrega': str(date.today()), 'estado_actividad': 'pendiente',
        'archivo_cronograma': SimpleUploadedFile('malware.exe', b'MZ', content_type='application/octet-stream'),
    }, format='multipart')
    assert resp.status_code == 400
    assert 'archivo_cronograma' in resp.json()


@pytest.mark.django_db
def test_informe_rechaza_extension_no_permitida(
    auth_client, admin_user, semillero_aprobado, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    client = auth_client(admin_user)
    resp = client.post('/api/v1/reportes/', {
        'semillero': semillero_aprobado.id,
        'titulo': 'Informe mensual', 'tipo': 'mensual', 'semestre': '2025-1',
        'archivo': SimpleUploadedFile('malware.exe', b'MZ', content_type='application/octet-stream'),
    }, format='multipart')
    assert resp.status_code == 400
    assert 'archivo' in resp.json()


@pytest.mark.django_db
def test_user_foto_rechaza_extension_no_permitida(auth_client, admin_user, estudiante, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    client = auth_client(admin_user)
    resp = client.patch(f'/api/v1/config/users/{estudiante.id}/', {
        'foto': SimpleUploadedFile('malware.exe', b'MZ', content_type='application/octet-stream'),
    }, format='multipart')
    assert resp.status_code == 400
    assert 'foto' in resp.json()


@pytest.mark.django_db
def test_semillero_logo_rechaza_extension_no_permitida(
    auth_client, admin_user, grupo, director_semillero, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    client = auth_client(admin_user)
    resp = client.post('/api/v1/core/semilleros/', {
        'nombre': 'Semillero X', 'codigo': 'SX1', 'objetivo': 'obj',
        'fecha_creacion': str(date.today()),
        'grupo_investigacion': grupo.id, 'director': director_semillero.id,
        'logo': SimpleUploadedFile('malware.exe', b'MZ', content_type='application/octet-stream'),
    }, format='multipart')
    assert resp.status_code == 400
    assert 'logo' in resp.json()


# ---------------------------------------------------------------------------
# T2.5 — evidencia ahora acepta .xlsx, como el resto de rutas unificadas
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_evidencia_acepta_xlsx_tras_la_unificacion(
    auth_client, lider_estudiantil, actividad, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    client = auth_client(lider_estudiantil)
    resp = client.post('/api/v1/core/avances/', {
        'actividad': actividad.id, 'tipo': 'documento',
        'titulo': 'Planilla', 'descripcion': 'desc',
        'archivo': SimpleUploadedFile(
            'planilla.xlsx', b'PK\x03\x04xlsx-fake',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ),
    }, format='multipart')
    assert resp.status_code == 201, resp.content
