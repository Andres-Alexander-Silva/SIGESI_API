"""Smoke tests for /api/v1/core/grupos-investigacion/.

GrupoInvestigacionViewSet uses IsAuthenticated only — any authenticated user
can read/write. Tests document that behavior.
"""
from datetime import date

import pytest


URL = '/api/v1/core/grupos-investigacion/'


@pytest.mark.django_db
def test_admin_can_create_grupo(auth_client, admin_user, programa, director_grupo):
    client = auth_client(admin_user)
    resp = client.post(URL, {
        'nombre': 'Grupo Nuevo',
        'codigo': 'GN',
        'descripcion': 'desc',
        'fecha_creacion': str(date.today()),
        'programa_academico': programa.id,
        'director': director_grupo.id,
        'is_active': True,
    }, format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_estudiante_can_list_grupos(auth_client, estudiante, grupo):
    client = auth_client(estudiante)
    resp = client.get(URL)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_unauthenticated_returns_401(api_client):
    resp = api_client.get(URL)
    assert resp.status_code == 401
