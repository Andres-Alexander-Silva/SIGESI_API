"""Invariante de roles: todo líder estudiantil es también estudiante."""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_lider_user_gana_rol_estudiante_al_crear():
    user = User.objects.create(
        username='lider_x', cedula='LID001',
        correo_personal='liderx@example.com', email='liderx@ufps.edu.co',
        roles=['lider_estudiantil'],
    )
    user.refresh_from_db()
    assert 'lider_estudiantil' in user.roles
    assert 'estudiante' in user.roles


@pytest.mark.django_db
def test_lider_no_duplica_estudiante_si_ya_lo_tiene():
    user = User.objects.create(
        username='lider_y', cedula='LID002',
        correo_personal='lidery@example.com', email='lidery@ufps.edu.co',
        roles=['lider_estudiantil', 'estudiante'],
    )
    user.refresh_from_db()
    assert user.roles.count('estudiante') == 1


@pytest.mark.django_db
def test_usuario_sin_lider_no_recibe_estudiante():
    user = User.objects.create(
        username='dir_x', cedula='DIR001',
        correo_personal='dirx@example.com', email='dirx@ufps.edu.co',
        roles=['director_grupo'],
    )
    user.refresh_from_db()
    assert user.roles == ['director_grupo']


@pytest.mark.django_db
def test_fixture_lider_tiene_ambos_roles(lider_estudiantil):
    assert 'lider_estudiantil' in lider_estudiantil.roles
    assert 'estudiante' in lider_estudiantil.roles
