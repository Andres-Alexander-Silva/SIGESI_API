"""Regresión: los endpoints de reportes e informes lanzaban 500
(AttributeError) para todo rol distinto de administrador porque referenciaban
``User.RolChoices.DOCENTE`` y ``User.RolChoices.DIRECTOR_PROGRAMA``, roles que
nunca existieron en el modelo.
"""
import pytest

REPORTE_PROYECTOS_URL = '/api/v1/reportes/proyectos/'
REPORTE_SEMILLEROS_URL = '/api/v1/reportes/semilleros/'
INFORMES_URL = '/api/v1/reportes/'

ROLES = ['admin_user', 'director_grupo', 'director_semillero', 'estudiante', 'lider_estudiantil']


@pytest.mark.django_db
@pytest.mark.parametrize('role_fixture', ROLES)
def test_reporte_proyectos_no_falla_para_ningun_rol(request, auth_client, role_fixture, proyecto):
    user = request.getfixturevalue(role_fixture)
    client = auth_client(user)
    resp = client.get(REPORTE_PROYECTOS_URL)
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
@pytest.mark.parametrize('role_fixture', ROLES)
def test_reporte_semilleros_no_falla_para_ningun_rol(request, auth_client, role_fixture, semillero_aprobado):
    user = request.getfixturevalue(role_fixture)
    client = auth_client(user)
    resp = client.get(REPORTE_SEMILLEROS_URL)
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
@pytest.mark.parametrize('role_fixture', ROLES)
def test_listar_informes_no_falla_para_ningun_rol(request, auth_client, role_fixture, semillero_aprobado):
    user = request.getfixturevalue(role_fixture)
    client = auth_client(user)
    resp = client.get(INFORMES_URL)
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
def test_director_semillero_puede_generar_informe(auth_client, director_semillero, semillero_aprobado):
    client = auth_client(director_semillero)
    resp = client.post(f'{INFORMES_URL}generar/', {
        'semillero_id': semillero_aprobado.id,
        'tipo': 'semestral',
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_informe_archive_download(auth_client, admin_user, semillero_aprobado, settings, tmp_path):
    """Regresión de HU-021 F3: el cliente descargaba el informe con un `href`
    directo al campo `archivo` crudo, que solo se sirve en DEBUG (ver
    config/urls.py) y no manda el Bearer. Ahora usa este endpoint."""
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.sigesi.models import Informe

    settings.MEDIA_ROOT = str(tmp_path)
    informe = Informe.objects.create(
        semillero=semillero_aprobado, titulo='Informe mensual',
        tipo='mensual', semestre='2025-1',
        archivo=SimpleUploadedFile('informe.pdf', b'%PDF-1.4', content_type='application/pdf'),
    )
    client = auth_client(admin_user)
    resp = client.get(f'{INFORMES_URL}{informe.id}/archive/download/')
    assert resp.status_code == 200
    assert resp['Content-Disposition'].startswith('attachment')


@pytest.mark.django_db
def test_informe_archive_download_sin_archivo_404(auth_client, admin_user, semillero_aprobado):
    from apps.sigesi.models import Informe

    informe = Informe.objects.create(
        semillero=semillero_aprobado, titulo='Sin archivo',
        tipo='mensual', semestre='2025-1',
    )
    client = auth_client(admin_user)
    resp = client.get(f'{INFORMES_URL}{informe.id}/archive/download/')
    assert resp.status_code == 404
