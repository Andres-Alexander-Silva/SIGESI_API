import pytest

URL = '/api/v1/config/users/bulk-upload/formato/'


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
