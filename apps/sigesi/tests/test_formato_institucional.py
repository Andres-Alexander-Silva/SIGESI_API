"""Tests del repositorio administrable de formatos institucionales (HU-021, F4).

Reemplaza el catálogo hardcodeado que vivía en formatos_docente_view.py
(FORMATOS_DOCENTE): antes, agregar/versionar/retirar un formato exigía editar
código y desplegar. FormatoInstitucionalViewSet es el CRUD; el endpoint
bulk (test_formatos_docente.py) arma el .zip desde este mismo modelo.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.sigesi.models import FormatoInstitucional

URL = '/api/v1/informes/formatos-institucionales/'


def _docx(name='formato.docx'):
    return SimpleUploadedFile(
        name, b'PK\x03\x04docx-fake',
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )


# ---------------------------------------------------------------------------
# T4.1 — CRUD por rol
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_admin_puede_crear_formato(auth_client, admin_user, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    client = auth_client(admin_user)
    resp = client.post(URL, {
        'slug': 'formato-nuevo', 'nombre': 'Formato Nuevo', 'categoria': 'gestion',
        'archivo': _docx(),
    }, format='multipart')
    assert resp.status_code == 201, resp.content
    assert FormatoInstitucional.objects.filter(slug='formato-nuevo').exists()


@pytest.mark.django_db
def test_admin_puede_editar_y_eliminar_formato(auth_client, admin_user, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    formato = FormatoInstitucional.objects.create(
        slug='editable', nombre='Editable', categoria='gestion', archivo=_docx(),
    )
    client = auth_client(admin_user)

    resp = client.patch(f'{URL}{formato.slug}/', {'nombre': 'Renombrado'}, format='json')
    assert resp.status_code == 200, resp.content
    assert resp.json()['nombre'] == 'Renombrado'

    resp = client.delete(f'{URL}{formato.slug}/')
    assert resp.status_code == 204
    assert not FormatoInstitucional.objects.filter(slug='editable').exists()


@pytest.mark.django_db
def test_director_semillero_no_puede_escribir_pero_si_leer(
    auth_client, director_semillero, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    formato = FormatoInstitucional.objects.create(
        slug='solo-lectura', nombre='Solo lectura', categoria='gestion', archivo=_docx(),
    )
    client = auth_client(director_semillero)

    resp = client.get(URL)
    assert resp.status_code == 200

    resp = client.post(URL, {
        'slug': 'intento', 'nombre': 'Intento', 'categoria': 'gestion', 'archivo': _docx(),
    }, format='multipart')
    assert resp.status_code == 403

    resp = client.patch(f'{URL}{formato.slug}/', {'nombre': 'x'}, format='json')
    assert resp.status_code == 403

    resp = client.delete(f'{URL}{formato.slug}/')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_estudiante_no_tiene_acceso(auth_client, estudiante, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    FormatoInstitucional.objects.create(
        slug='oculto', nombre='Oculto', categoria='gestion', archivo=_docx(),
    )
    client = auth_client(estudiante)
    assert client.get(URL).status_code == 403


# ---------------------------------------------------------------------------
# T4.2 — descarga individual por slug
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_descarga_formato_por_slug(auth_client, admin_user, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    FormatoInstitucional.objects.create(
        slug='descargable', nombre='Descargable', categoria='gestion', archivo=_docx(),
    )
    client = auth_client(admin_user)
    resp = client.get(f'{URL}descargable/archive/download/')
    assert resp.status_code == 200
    assert resp['Content-Disposition'].startswith('attachment')


@pytest.mark.django_db
def test_descarga_slug_inexistente_404(auth_client, admin_user):
    client = auth_client(admin_user)
    resp = client.get(f'{URL}no-existe/archive/download/')
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# T4.3 — el .zip del bulk endpoint sí filtra por tipo_vinculacion
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_zip_bulk_excluye_formato_exclusivo_de_otro_tipo_vinculacion(
    auth_client, admin_user, director_semillero, settings, tmp_path,
):
    """`informe-mensual` (tipo_vinculacion='catedratico') no debe aparecer en
    el .zip de un director de planta."""
    import io
    import zipfile

    settings.MEDIA_ROOT = str(tmp_path)
    # Los 6 formatos sembrados por la migración de datos apuntan a rutas bajo
    # el MEDIA_ROOT real del proyecto; al forzar tmp_path aquí quedarían
    # inalcanzables, así que se desactivan para que el filtro estado=True
    # del endpoint bulk solo recoja los dos formatos que crea este test.
    FormatoInstitucional.objects.update(estado=False)

    FormatoInstitucional.objects.create(
        slug='general', nombre='General', categoria='gestion',
        archivo=_docx('general.docx'), tipo_vinculacion=None,
    )
    FormatoInstitucional.objects.create(
        slug='solo-catedratico', nombre='Solo Catedrático', categoria='mensual',
        archivo=_docx('solo_catedratico.docx'), tipo_vinculacion='catedratico',
    )
    director_semillero.tipo_vinculacion = 'planta'
    director_semillero.save()

    client = auth_client(admin_user)
    resp = client.get(f'/api/v1/informes/formularios-docente/?user={director_semillero.id}')
    assert resp.status_code == 200, resp.content[:200]

    contenido = b''.join(resp.streaming_content)
    with zipfile.ZipFile(io.BytesIO(contenido)) as zf:
        nombres = zf.namelist()

    assert 'general.docx' in nombres
    assert 'solo_catedratico.docx' not in nombres


# ---------------------------------------------------------------------------
# T4.6 — la migración de datos preserva los 6 slugs originales
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_migracion_preserva_los_seis_slugs_originales():
    slugs_originales = {
        'plan-accion-semillero', 'plan-accion-grupo', 'gestion-semillero',
        'solicitud-horas-directores', 'control-cumplimiento-produccion', 'informe-mensual',
    }
    slugs_en_bd = set(FormatoInstitucional.objects.values_list('slug', flat=True))
    assert slugs_originales <= slugs_en_bd
