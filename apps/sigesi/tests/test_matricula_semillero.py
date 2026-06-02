"""Smoke tests for /api/v1/core/inscripciones/ (MatriculaSemillero)."""
from datetime import date

import pytest

from apps.sigesi.models import Semillero


URL = '/api/v1/core/inscripciones/'


def _semillero_aprobado(grupo, director=None, lider=None, codigo='SX'):
    """Crea un semillero aprobado auxiliar para casos de alcance."""
    return Semillero.objects.create(
        nombre=f'Semillero {codigo}',
        codigo=codigo,
        objetivo='Aux.',
        fecha_creacion=date.today(),
        grupo_investigacion=grupo,
        director=director,
        lider_estudiantil=lider,
        estado_aval=Semillero.EstadoAvalChoices.APROBADO,
    )


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


@pytest.mark.django_db
def test_director_designates_new_lider_replaces_previous(
    auth_client, director_semillero, estudiante, lider_estudiantil, semillero_aprobado
):
    """Designar un nuevo líder reasigna el FK del semillero; el anterior conserva
    su matrícula y sus roles globales, pero deja de ser el líder del semillero."""
    # El semillero ya tiene a `lider_estudiantil` como líder (fixture).
    assert semillero_aprobado.lider_estudiantil == lider_estudiantil
    assert semillero_aprobado.director == director_semillero

    client = auth_client(director_semillero)
    resp = client.post(URL, {
        'estudiante': estudiante.id,
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
        'rol_en_semillero': 'lider_estudiantil',
    }, format='json')
    assert resp.status_code == 201, resp.content

    semillero_aprobado.refresh_from_db()
    estudiante.refresh_from_db()
    lider_estudiantil.refresh_from_db()

    # El nuevo líder del semillero es el estudiante recién inscrito.
    assert semillero_aprobado.lider_estudiantil_id == estudiante.id
    # Gana el rol global lider_estudiantil (y estudiante por el invariante).
    assert 'lider_estudiantil' in estudiante.roles
    assert 'estudiante' in estudiante.roles
    # El líder anterior conserva sus roles globales (puede liderar otro semillero).
    assert 'lider_estudiantil' in lider_estudiantil.roles
    # La inscripción se refleja como líder en el serializer de lectura.
    assert resp.json()['data']['rol_en_semillero'] == 'lider_estudiantil'


@pytest.mark.django_db
def test_estudiante_cannot_self_designate_as_lider(
    auth_client, estudiante, semillero_aprobado
):
    """Un estudiante no puede autodesignarse líder del semillero."""
    client = auth_client(estudiante)
    resp = client.post(URL, {
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
        'rol_en_semillero': 'lider_estudiantil',
    }, format='json')
    assert resp.status_code == 400
    assert 'rol_en_semillero' in resp.json()


@pytest.mark.django_db
def test_default_enrollment_keeps_existing_lider(
    auth_client, director_semillero, estudiante, lider_estudiantil, semillero_aprobado
):
    """Inscribir con rol por defecto (estudiante) no cambia el líder del semillero."""
    client = auth_client(director_semillero)
    resp = client.post(URL, {
        'estudiante': estudiante.id,
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 201, resp.content

    semillero_aprobado.refresh_from_db()
    assert semillero_aprobado.lider_estudiantil_id == lider_estudiantil.id
    assert resp.json()['data']['rol_en_semillero'] == 'estudiante'


@pytest.mark.django_db
def test_multi_role_user_with_student_and_director_can_self_enroll(
    auth_client, semillero_aprobado
):
    """A user who has both 'director_semillero' and 'estudiante' roles can successfully
    self-enroll in a semillero they do not direct.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    # Create user with both roles
    multi_role_user = User.objects.create(
        username='multirole1',
        cedula='CC999999',
        correo_personal='multirole1@example.com',
        email='multirole1@inst.edu',
        first_name='Multi',
        last_name='Role',
        roles=['director_semillero', 'estudiante'],
        is_active=True
    )
    multi_role_user.set_password('x')
    multi_role_user.save()

    # Ensure the semillero is directed by someone else
    assert semillero_aprobado.director != multi_role_user

    client = auth_client(multi_role_user)
    resp = client.post(URL, {
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
    }, format='json')
    
    assert resp.status_code == 201, resp.content
    assert resp.json()['data']['estudiante'] == multi_role_user.id


@pytest.mark.django_db
def test_multi_role_user_with_student_and_director_can_self_enroll_with_explicit_id(
    auth_client, semillero_aprobado
):
    """A user who has both 'director_semillero' and 'estudiante' roles can successfully
    self-enroll in a semillero they do not direct, even when passing their own ID explicitly.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    # Create user with both roles
    multi_role_user = User.objects.create(
        username='multirole2',
        cedula='CC999998',
        correo_personal='multirole2@example.com',
        email='multirole2@inst.edu',
        first_name='Multi',
        last_name='Role Two',
        roles=['director_semillero', 'estudiante'],
        is_active=True
    )
    multi_role_user.set_password('x')
    multi_role_user.save()

    # Ensure the semillero is directed by someone else
    assert semillero_aprobado.director != multi_role_user

    client = auth_client(multi_role_user)
    resp = client.post(URL, {
        'estudiante': multi_role_user.id,
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
    }, format='json')

    assert resp.status_code == 201, resp.content
    assert resp.json()['data']['estudiante'] == multi_role_user.id


# ---------------------------------------------------------------------------
# Alcance por rol de gestión (director de grupo / semillero / líder)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_director_grupo_can_enroll_student_in_their_group_semillero(
    auth_client, director_grupo, otro_estudiante, semillero_aprobado
):
    """El director de grupo inscribe en semilleros de los grupos que dirige."""
    # semillero_aprobado.grupo_investigacion.director == director_grupo (fixtures).
    client = auth_client(director_grupo)
    resp = client.post(URL, {
        'estudiante': otro_estudiante.id,
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.json()['data']['estudiante'] == otro_estudiante.id


@pytest.mark.django_db
def test_director_grupo_cannot_enroll_outside_their_group(
    auth_client, otro_estudiante, semillero_aprobado
):
    """Un director de grupo que no dirige el grupo del semillero queda fuera de alcance."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    ajeno = User.objects.create(
        username='dg_ajeno', cedula='CC700001',
        correo_personal='dgajeno@example.com', email='dgajeno@inst.edu',
        roles=['director_grupo'], is_active=True,
    )
    ajeno.set_password('x')
    ajeno.save()

    client = auth_client(ajeno)
    resp = client.post(URL, {
        'estudiante': otro_estudiante.id,
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 400
    assert 'alcance' in resp.content.decode().lower()


@pytest.mark.django_db
def test_lider_can_enroll_student_in_led_semillero(
    auth_client, lider_estudiantil, otro_estudiante, semillero_aprobado
):
    """El líder estudiantil inscribe a otros en los semilleros que lidera."""
    # semillero_aprobado.lider_estudiantil == lider_estudiantil (fixtures).
    client = auth_client(lider_estudiantil)
    resp = client.post(URL, {
        'estudiante': otro_estudiante.id,
        'semillero': semillero_aprobado.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.json()['data']['estudiante'] == otro_estudiante.id


@pytest.mark.django_db
def test_lider_cannot_enroll_in_unled_semillero(
    auth_client, lider_estudiantil, otro_estudiante, grupo, director_semillero
):
    """El líder no puede inscribir a otros en un semillero que no lidera."""
    otro_sem = _semillero_aprobado(grupo, director=director_semillero, codigo='S-NL')
    client = auth_client(lider_estudiantil)
    resp = client.post(URL, {
        'estudiante': otro_estudiante.id,
        'semillero': otro_sem.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 400
    assert 'alcance' in resp.content.decode().lower()


@pytest.mark.django_db
def test_lider_can_self_enroll_in_any_semillero(
    auth_client, lider_estudiantil, grupo, director_semillero
):
    """El líder (que también es estudiante) puede autoinscribirse en cualquier semillero."""
    otro_sem = _semillero_aprobado(grupo, director=director_semillero, codigo='S-SELF')
    client = auth_client(lider_estudiantil)
    resp = client.post(URL, {
        'semillero': otro_sem.id,
        'semestre': '2025-1',
    }, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.json()['data']['estudiante'] == lider_estudiantil.id

