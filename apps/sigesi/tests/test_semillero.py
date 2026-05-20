"""Smoke tests for /api/v1/core/semilleros/ — CRUD + aval admin endpoint."""
from datetime import date

import pytest

from apps.sigesi.models import Semillero


URL = '/api/v1/core/semilleros/'


@pytest.mark.django_db
def test_admin_can_create_semillero(auth_client, admin_user, grupo, director_semillero):
    client = auth_client(admin_user)
    resp = client.post(URL, {
        'nombre': 'Semillero Nuevo',
        'codigo': 'SN1',
        'objetivo': 'Investigación.',
        'fecha_creacion': str(date.today()),
        'grupo_investigacion': grupo.id,
        'director': director_semillero.id,
    }, format='json')
    assert resp.status_code == 201, resp.content
    # Default aval is sin_aprobar — admin still has to approve via /aval/
    new = Semillero.objects.get(codigo='SN1')
    assert new.estado_aval == Semillero.EstadoAvalChoices.SIN_APROBAR


@pytest.mark.django_db
def test_director_cannot_change_estado_aval_via_regular_patch(
    auth_client, director_semillero, semillero_sin_aprobar
):
    """Aval fields are not in SemilleroCreateUpdateSerializer.fields."""
    client = auth_client(director_semillero)
    resp = client.patch(
        f'{URL}{semillero_sin_aprobar.id}/',
        {'estado_aval': 'aprobado'},
        format='json',
    )
    # Request may succeed (200) — the field is silently ignored, not rejected.
    assert resp.status_code in (200, 400)
    semillero_sin_aprobar.refresh_from_db()
    assert semillero_sin_aprobar.estado_aval == Semillero.EstadoAvalChoices.SIN_APROBAR


@pytest.mark.django_db
def test_aval_get_returns_state_for_any_authenticated(
    auth_client, estudiante, semillero_aprobado
):
    client = auth_client(estudiante)
    resp = client.get(f'{URL}{semillero_aprobado.id}/aval/')
    assert resp.status_code == 200
    assert resp.json()['estado_aval'] == 'aprobado'


@pytest.mark.django_db
def test_admin_aval_patch_to_aprobado_stamps_user_and_date(
    auth_client, admin_user, semillero_sin_aprobar
):
    from django.core.files.uploadedfile import SimpleUploadedFile
    pdf_file = SimpleUploadedFile("aval.pdf", b"%PDF-1.4 ... test pdf", content_type="application/pdf")
    client = auth_client(admin_user)
    resp = client.patch(
        f'{URL}{semillero_sin_aprobar.id}/aval/',
        {
            'estado_aval': 'aprobado',
            'tipo_documento': 'acta',
            'numero_acta': '0042',
            'archivo_aval': pdf_file
        },
        format='multipart',
    )
    assert resp.status_code == 200, resp.content

    semillero_sin_aprobar.refresh_from_db()
    assert semillero_sin_aprobar.estado_aval == Semillero.EstadoAvalChoices.APROBADO
    assert semillero_sin_aprobar.usuario_aprobacion_id == admin_user.id
    assert semillero_sin_aprobar.fecha_aprobacion is not None

    # Cleanup physical file created in test
    import os
    if semillero_sin_aprobar.archivo_aval and os.path.exists(semillero_sin_aprobar.archivo_aval.path):
        os.remove(semillero_sin_aprobar.archivo_aval.path)


@pytest.mark.django_db
def test_admin_aval_patch_to_aprobado_without_required_docs_returns_400(
    auth_client, admin_user, semillero_sin_aprobar
):
    client = auth_client(admin_user)
    resp = client.patch(
        f'{URL}{semillero_sin_aprobar.id}/aval/',
        {'estado_aval': 'aprobado'},
        format='multipart',
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_aval_patch_as_non_admin_returns_403(
    auth_client, director_semillero, semillero_sin_aprobar
):
    client = auth_client(director_semillero)
    resp = client.patch(
        f'{URL}{semillero_sin_aprobar.id}/aval/',
        {'estado_aval': 'aprobado', 'tipo_documento': 'acta', 'numero_acta': '0001'},
        format='multipart',
    )
    assert resp.status_code == 403


from django.core.files.uploadedfile import SimpleUploadedFile

@pytest.mark.django_db
def test_admin_aval_patch_with_pdf_succeeds(auth_client, admin_user, semillero_sin_aprobar):
    client = auth_client(admin_user)
    pdf_file = SimpleUploadedFile("aval.pdf", b"%PDF-1.4 ... test pdf content", content_type="application/pdf")
    resp = client.patch(
        f'{URL}{semillero_sin_aprobar.id}/aval/',
        {
            'estado_aval': 'aprobado',
            'tipo_documento': 'acta',
            'numero_acta': '0042',
            'archivo_aval': pdf_file
        },
        format='multipart'
    )
    assert resp.status_code == 200, resp.content
    semillero_sin_aprobar.refresh_from_db()
    assert semillero_sin_aprobar.estado_aval == Semillero.EstadoAvalChoices.APROBADO
    assert semillero_sin_aprobar.archivo_aval.name.endswith('.pdf')
    
    # Cleanup physical file created in test
    import os
    if semillero_sin_aprobar.archivo_aval and os.path.exists(semillero_sin_aprobar.archivo_aval.path):
        os.remove(semillero_sin_aprobar.archivo_aval.path)


@pytest.mark.django_db
def test_admin_aval_patch_with_invalid_extension_fails(auth_client, admin_user, semillero_sin_aprobar):
    client = auth_client(admin_user)
    txt_file = SimpleUploadedFile("aval.txt", b"some plain text", content_type="text/plain")
    resp = client.patch(
        f'{URL}{semillero_sin_aprobar.id}/aval/',
        {
            'estado_aval': 'aprobado',
            'tipo_documento': 'acta',
            'numero_acta': '0042',
            'archivo_aval': txt_file
        },
        format='multipart'
    )
    assert resp.status_code == 400
    assert "archivo_aval" in resp.json()
    assert "documento PDF" in resp.json()["archivo_aval"][0]


@pytest.mark.django_db
def test_admin_aval_patch_with_excessive_size_fails(auth_client, admin_user, semillero_sin_aprobar):
    client = auth_client(admin_user)
    # Generar datos de 5.1 MB
    large_data = b"a" * (5 * 1024 * 1024 + 1024)
    large_pdf = SimpleUploadedFile("large_aval.pdf", large_data, content_type="application/pdf")
    resp = client.patch(
        f'{URL}{semillero_sin_aprobar.id}/aval/',
        {
            'estado_aval': 'aprobado',
            'tipo_documento': 'acta',
            'numero_acta': '0042',
            'archivo_aval': large_pdf
        },
        format='multipart'
    )
    assert resp.status_code == 400
    assert "archivo_aval" in resp.json()
    assert "exceder los 5 MB" in resp.json()["archivo_aval"][0]


@pytest.mark.django_db
def test_admin_aval_patch_approve_without_file_fails(auth_client, admin_user, semillero_sin_aprobar):
    client = auth_client(admin_user)
    # Intentar aprobar con acta y tipo pero sin documento adjunto
    resp = client.patch(
        f'{URL}{semillero_sin_aprobar.id}/aval/',
        {
            'estado_aval': 'aprobado',
            'tipo_documento': 'acta',
            'numero_acta': '0042'
        },
        format='multipart'
    )
    assert resp.status_code == 400
    assert "non_field_errors" in resp.json()
    assert "cargar el documento digital" in resp.json()["non_field_errors"][0]


@pytest.mark.django_db
def test_admin_aval_patch_overwrites_and_cleans_up_old_file(auth_client, admin_user, semillero_sin_aprobar):
    client = auth_client(admin_user)
    
    # 1. Cargar primer PDF
    pdf_file_1 = SimpleUploadedFile("aval1.pdf", b"%PDF-1.4 first", content_type="application/pdf")
    resp = client.patch(
        f'{URL}{semillero_sin_aprobar.id}/aval/',
        {
            'estado_aval': 'aprobado',
            'tipo_documento': 'acta',
            'numero_acta': '0042',
            'archivo_aval': pdf_file_1
        },
        format='multipart'
    )
    assert resp.status_code == 200
    semillero_sin_aprobar.refresh_from_db()
    old_file_path = semillero_sin_aprobar.archivo_aval.path
    import os
    assert os.path.exists(old_file_path)

    # 2. Cargar segundo PDF (debería limpiar el primero físicamente)
    pdf_file_2 = SimpleUploadedFile("aval2.pdf", b"%PDF-1.4 second", content_type="application/pdf")
    resp = client.patch(
        f'{URL}{semillero_sin_aprobar.id}/aval/',
        {
            'archivo_aval': pdf_file_2
        },
        format='multipart'
    )
    assert resp.status_code == 200
    
    # 3. Validar que el primer archivo fue eliminado
    assert not os.path.exists(old_file_path)
    
    # Limpieza final del segundo archivo
    semillero_sin_aprobar.refresh_from_db()
    new_file_path = semillero_sin_aprobar.archivo_aval.path
    if os.path.exists(new_file_path):
        os.remove(new_file_path)
