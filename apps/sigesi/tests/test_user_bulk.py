import io

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.sigesi.models import User
from apps.sigesi.views.config.user_view import _cell_to_str

URL = '/api/v1/config/users/bulk-upload/formato/'
UPLOAD_URL = '/api/v1/config/users/bulk-upload/'

HEADERS = [
    'Username', 'Cédula', 'Nombres', 'Apellidos', 'Email Institucional',
    'Correo Personal', 'Teléfono', 'Roles', 'Código', 'Programa Académico',
]

XLSX_CT = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def _build_xlsx(rows):
    """Construye un .xlsx en memoria con la cabecera estándar y las filas dadas."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(HEADERS)
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return SimpleUploadedFile('carga.xlsx', buffer.read(), content_type=XLSX_CT)


# ---------------------------------------------------------------- _cell_to_str

def test_cell_to_str_float_entero_sin_decimal():
    assert _cell_to_str(1090123456.0) == '1090123456'


def test_cell_to_str_int():
    assert _cell_to_str(1090123456) == '1090123456'


def test_cell_to_str_texto_intacto():
    assert _cell_to_str('  1090123456  ') == '1090123456'


# --------------------------------------------------------------- bulk ingest

@pytest.mark.django_db
def test_bulk_upload_cedula_numerica_no_arrastra_decimal(auth_client, admin_user):
    """Una cédula que llega como float de Excel se guarda sin el sufijo '.0'."""
    client = auth_client(admin_user)
    # Username vacío -> debe heredar la cédula ya normalizada.
    rows = [['', 1090123456.0, 'Ana', 'Pérez', 'ana@ufps.edu.co',
             'ana@gmail.com', 3001234567.0, 'estudiante', 172001.0, '']]
    resp = client.post(UPLOAD_URL, {'file': _build_xlsx(rows)}, format='multipart')

    assert resp.status_code == 200
    assert resp.data['creados'] == 1

    user = User.objects.get(correo_personal='ana@gmail.com')
    assert user.cedula == '1090123456'
    assert user.username == '1090123456'
    assert user.codigo_estudiantil == '172001'
    assert user.telefono == '3001234567'


@pytest.mark.django_db
def test_bulk_upload_cedula_texto_se_mantiene(auth_client, admin_user):
    """Una cédula escrita como texto no debe alterarse (regresión)."""
    client = auth_client(admin_user)
    rows = [['', '1090123456', 'Luis', 'Gómez', 'luis@ufps.edu.co',
             'luis@gmail.com', '', 'estudiante', '', '']]
    resp = client.post(UPLOAD_URL, {'file': _build_xlsx(rows)}, format='multipart')

    assert resp.status_code == 200
    user = User.objects.get(correo_personal='luis@gmail.com')
    assert user.cedula == '1090123456'


@pytest.mark.django_db
def test_bulk_upload_requiere_rol_administrador(auth_client, estudiante):
    client = auth_client(estudiante)
    rows = [['', 123.0, 'X', 'Y', 'x@ufps.edu.co', 'x@gmail.com', '', 'estudiante', '', '']]
    resp = client.post(UPLOAD_URL, {'file': _build_xlsx(rows)}, format='multipart')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_unauthenticated_cannot_download_formato(api_client):
    resp = api_client.get(URL)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_authenticated_user_can_download_formato(auth_client, estudiante):
    client = auth_client(estudiante)
    resp = client.get(URL)
    assert resp.status_code == 200
    assert resp['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'attachment' in resp['Content-Disposition']
    assert 'FORMATO_DE_REGISTRO_DE_ESTUDIANTES.xlsx' in resp['Content-Disposition']
