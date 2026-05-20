"""Smoke tests for /api/v1/core/inscripciones/ (MatriculaSemillero)."""
import pytest


URL = '/api/v1/core/inscripciones/'


@pytest.mark.django_db
def test_estudiante_inscribes_in_aprobado_semillero(
    auth_client, estudiante, semillero_aprobado
):
    client = auth_client(estudiante)
    resp = client.post(URL, {
        'estudiante': estudiante.id,
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_estudiante_cannot_inscribe_in_sin_aprobar_semillero(
    auth_client, estudiante, semillero_sin_aprobar
):
    """Aval gate: writes against a non-approved semillero must fail for non-admin."""
    client = auth_client(estudiante)
    resp = client.post(URL, {
        'estudiante': estudiante.id,
        'semillero': semillero_sin_aprobar.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 400
    assert 'aval aprobado' in resp.content.decode().lower()


@pytest.mark.django_db
def test_admin_can_inscribe_in_sin_aprobar_semillero(
    auth_client, admin_user, otro_estudiante, semillero_sin_aprobar
):
    """Admin bypasses the aval gate."""
    client = auth_client(admin_user)
    resp = client.post(URL, {
        'estudiante': otro_estudiante.id,
        'semillero': semillero_sin_aprobar.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_estudiante_auto_assigns_themselves_when_estudiante_omitted(
    auth_client, estudiante, semillero_aprobado
):
    """If the authenticated user is an estudiante and omits the estudiante ID, it auto-assigns."""
    client = auth_client(estudiante)
    resp = client.post(URL, {
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.json()['data']['estudiante'] == estudiante.id


@pytest.mark.django_db
def test_estudiante_cannot_enroll_another_student(
    auth_client, estudiante, otro_estudiante, semillero_aprobado
):
    """An estudiante must not be allowed to enroll another student's ID."""
    client = auth_client(estudiante)
    resp = client.post(URL, {
        'estudiante': otro_estudiante.id,
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 400
    assert 'estudiante' in resp.json()
    assert 'solo puede inscribirse a sí mismo' in resp.json()['estudiante'][0]


@pytest.mark.django_db
def test_admin_and_director_must_provide_estudiante(
    auth_client, admin_user, director_semillero, semillero_aprobado
):
    """Admins and directors must explicitly provide the estudiante field."""
    # Test for Admin
    client_admin = auth_client(admin_user)
    resp_admin = client_admin.post(URL, {
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp_admin.status_code == 400
    assert 'estudiante' in resp_admin.json()
    assert 'Debe indicar el estudiante a inscribir.' in resp_admin.json()['estudiante'][0]

    # Test for Director
    client_dir = auth_client(director_semillero)
    resp_dir = client_dir.post(URL, {
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp_dir.status_code == 400
    assert 'estudiante' in resp_dir.json()
    assert 'Debe indicar el estudiante a inscribir.' in resp_dir.json()['estudiante'][0]


@pytest.mark.django_db
def test_director_can_enroll_student_in_their_semillero(
    auth_client, director_semillero, estudiante, semillero_aprobado
):
    """A director of semillero can successfully enroll a student in a semillero they direct."""
    # Ensure the semillero's director is the director_semillero
    semillero_aprobado.director = director_semillero
    semillero_aprobado.save()

    client = auth_client(director_semillero)
    resp = client.post(URL, {
        'estudiante': estudiante.id,
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.json()['data']['estudiante'] == estudiante.id
    assert resp.json()['data']['semillero'] == semillero_aprobado.id
