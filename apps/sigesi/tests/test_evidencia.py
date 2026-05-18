"""Smoke tests for /api/v1/core/avances/ (Evidencia model)."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


URL = '/api/v1/core/avances/'


def _pdf(name='evidencia.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 fake content', content_type='application/pdf')


@pytest.mark.django_db
def test_lider_can_upload_evidencia_on_aprobado_proyecto(
    auth_client, lider_estudiantil, actividad
):
    client = auth_client(lider_estudiantil)
    resp = client.post(URL, {
        'actividad': actividad.id,
        'tipo': 'documento',
        'titulo': 'Acta 1',
        'descripcion': 'Acta de la reunión inicial del proyecto.',
        'archivo': _pdf(),
    }, format='multipart')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_evidencia_create_when_semillero_not_aprobado_returns_400(
    auth_client, director_semillero, semillero_sin_aprobar, lider_estudiantil
):
    from datetime import date
    from apps.sigesi.models import Proyecto, Actividad
    p = Proyecto.objects.create(
        titulo='Pno', codigo='PNO3', descripcion='d', objetivo_general='o',
        director=director_semillero,
    )
    p.semilleros.set([semillero_sin_aprobar])
    a = Actividad.objects.create(
        proyecto=p, titulo='t', descripcion='d', responsable=director_semillero,
        fecha_inicio=date.today(), fecha_fin=date.today(),
    )

    client = auth_client(director_semillero)
    resp = client.post(URL, {
        'actividad': a.id,
        'tipo': 'documento',
        'titulo': 'X',
        'descripcion': 'Descripción suficiente.',
        'archivo': _pdf(),
    }, format='multipart')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_evidencia_file_extension_validator_rejects_exe(
    auth_client, lider_estudiantil, actividad
):
    client = auth_client(lider_estudiantil)
    bad = SimpleUploadedFile('virus.exe', b'MZ binary', content_type='application/octet-stream')
    resp = client.post(URL, {
        'actividad': actividad.id,
        'tipo': 'documento',
        'titulo': 'X',
        'descripcion': 'desc',
        'archivo': bad,
    }, format='multipart')
    assert resp.status_code == 400
