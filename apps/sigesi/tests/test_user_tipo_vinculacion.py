"""Invariante de tipo_vinculacion: solo un director de semillero puede tenerlo.

Cubre las tres capas de la regla:
- ``User.save()`` anula ``tipo_vinculacion`` para roles que no sean director de
  semillero (red de seguridad para CRUD, carga masiva, admin y shell).
- El CRUD de usuarios responde 400 si se envía ``tipo_vinculacion`` para un no
  director.
- La función ``backfill`` de la migración 0023 rellena 'catedratico' en los
  directores preexistentes sin valor.
"""
import importlib

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model

User = get_user_model()

USERS_URL = '/api/v1/config/users/'


def _payload(**overrides):
    """Payload base válido para crear un usuario por el CRUD público."""
    data = {
        'username': 'nuevo_user',
        'cedula': 'CC900001',
        'correo_personal': 'nuevo_user@example.com',
        'password': 'password123',
        'first_name': 'Nuevo',
        'last_name': 'Usuario',
        'codigo_estudiantil': '900001',
        'roles': ['estudiante'],
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Invariante a nivel de modelo (save)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_save_anula_tipo_vinculacion_para_no_director():
    user = User.objects.create(
        username='est_x', cedula='EST001',
        correo_personal='estx@example.com', email='estx@ufps.edu.co',
        roles=['estudiante'], tipo_vinculacion='catedratico',
    )
    user.refresh_from_db()
    assert user.tipo_vinculacion is None


@pytest.mark.django_db
def test_save_conserva_tipo_vinculacion_para_director():
    user = User.objects.create(
        username='dir_s', cedula='DIRS01',
        correo_personal='dirs@example.com', email='dirs@ufps.edu.co',
        roles=['director_semillero'], tipo_vinculacion='planta',
    )
    user.refresh_from_db()
    assert user.tipo_vinculacion == 'planta'


@pytest.mark.django_db
def test_save_anula_al_quitar_rol_director(director_semillero):
    director_semillero.tipo_vinculacion = 'catedratico'
    director_semillero.save()
    # Se le retira el rol director de semillero.
    director_semillero.roles = ['estudiante']
    director_semillero.save()
    director_semillero.refresh_from_db()
    assert director_semillero.tipo_vinculacion is None


# ---------------------------------------------------------------------------
# CRUD — 400 para no directores, feliz para directores
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_crud_create_400_no_director_con_tipo_vinculacion(auth_client, admin_user):
    resp = auth_client(admin_user).post(
        USERS_URL,
        _payload(roles=['estudiante'], tipo_vinculacion='catedratico'),
        format='json',
    )
    assert resp.status_code == 400
    assert 'tipo_vinculacion' in resp.json()


@pytest.mark.django_db
def test_crud_create_director_con_tipo_vinculacion(auth_client, admin_user):
    resp = auth_client(admin_user).post(
        USERS_URL,
        _payload(
            username='dir_crud', cedula='CCDIR01',
            correo_personal='dircrud@example.com', codigo_estudiantil='dir01',
            roles=['director_semillero'], tipo_vinculacion='planta',
        ),
        format='json',
    )
    assert resp.status_code == 201, resp.content[:300]
    creado = User.objects.get(username='dir_crud')
    assert creado.tipo_vinculacion == 'planta'


@pytest.mark.django_db
def test_crud_patch_400_no_director(auth_client, admin_user, estudiante):
    resp = auth_client(admin_user).patch(
        f'{USERS_URL}{estudiante.id}/',
        {'tipo_vinculacion': 'planta'},
        format='json',
    )
    assert resp.status_code == 400
    assert 'tipo_vinculacion' in resp.json()


@pytest.mark.django_db
def test_crud_patch_director_actualiza_tipo_vinculacion(auth_client, admin_user, director_semillero):
    resp = auth_client(admin_user).patch(
        f'{USERS_URL}{director_semillero.id}/',
        {'tipo_vinculacion': 'planta'},
        format='json',
    )
    assert resp.status_code == 200, resp.content[:300]
    director_semillero.refresh_from_db()
    assert director_semillero.tipo_vinculacion == 'planta'


# ---------------------------------------------------------------------------
# Migración de backfill (0023)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_backfill_rellena_director_sin_valor(director_semillero, estudiante):
    # Simula el estado previo a la migración: director con tipo_vinculacion null.
    User.objects.filter(pk=director_semillero.pk).update(tipo_vinculacion=None)
    User.objects.filter(pk=estudiante.pk).update(tipo_vinculacion=None)

    migracion = importlib.import_module(
        'apps.sigesi.migrations.0023_backfill_tipo_vinculacion'
    )
    migracion.backfill(django_apps, None)

    director_semillero.refresh_from_db()
    estudiante.refresh_from_db()
    assert director_semillero.tipo_vinculacion == 'catedratico'
    assert estudiante.tipo_vinculacion is None
