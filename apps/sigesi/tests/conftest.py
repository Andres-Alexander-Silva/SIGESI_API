"""Shared fixtures for the SIGESI test suite."""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.sigesi.models import (
    Actividad,
    CronogramaProyecto,
    GrupoInvestigacion,
    LineaInvestigacion,
    ProgramaAcademico,
    Proyecto,
    Semillero,
)

User = get_user_model()


@pytest.fixture(autouse=True)
def _envio_correo_sincrono(settings):
    """Fuerza el envío de correo síncrono y las tareas Celery en línea.

    En producción el correo se delega (hilo o Celery), lo que haría no
    determinista la verificación de ``mail.outbox``. Aquí forzamos el envío
    dentro de la petición y la ejecución eager de Celery.
    """
    settings.EMAIL_DELIVERY = 'sync'
    settings.CELERY_TASK_ALWAYS_EAGER = True


# ---------------------------------------------------------------------------
# Users — one per role. Password is always 'x' so login tests can use it.
# ---------------------------------------------------------------------------

def _make_user(roles, **overrides):
    n = User.objects.count() + 1
    defaults = {
        'username': f'user{n}',
        'cedula': f'CC{n:06d}',
        'correo_personal': f'user{n}@example.com',
        'email': f'user{n}@inst.edu',
        'first_name': f'First{n}',
        'last_name': f'Last{n}',
        'roles': roles,
        'is_active': True,
    }
    defaults.update(overrides)
    user = User.objects.create(**defaults)
    user.set_password('x')
    user.save()
    return user


@pytest.fixture
def admin_user(db):
    return _make_user(['administrador'])


@pytest.fixture
def director_grupo(db):
    return _make_user(['director_grupo'])


@pytest.fixture
def director_semillero(db):
    return _make_user(['director_semillero'])


@pytest.fixture
def lider_estudiantil(db):
    return _make_user(['lider_estudiantil'])


@pytest.fixture
def estudiante(db):
    return _make_user(['estudiante'])


@pytest.fixture
def otro_estudiante(db):
    return _make_user(['estudiante'])


# ---------------------------------------------------------------------------
# API client + auth helper
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client):
    """Return a function that authenticates the api_client as the given user.

    Uses force_authenticate, which bypasses the JWT middleware path. JWT itself
    is exercised end-to-end in test_auth.py.
    """
    def _auth(user):
        api_client.force_authenticate(user=user)
        return api_client

    return _auth


# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def programa(db):
    return ProgramaAcademico.objects.create(
        nombre='Ing. Sistemas',
        codigo='IS',
        facultad='Facultad de Ingeniería',
    )


@pytest.fixture
def linea(db):
    return LineaInvestigacion.objects.create(
        nombre='Inteligencia Artificial',
        descripcion='IA aplicada',
    )


@pytest.fixture
def grupo(db, programa, director_grupo):
    return GrupoInvestigacion.objects.create(
        nombre='Grupo Alpha',
        codigo='G1',
        fecha_creacion=date.today(),
        programa_academico=programa,
        director=director_grupo,
    )


@pytest.fixture
def semillero_aprobado(db, grupo, director_semillero, lider_estudiantil):
    """Semillero with estado_aval=APROBADO — required for most dependent writes."""
    return Semillero.objects.create(
        nombre='Semillero Beta',
        codigo='S1',
        objetivo='Investigación aplicada en IA.',
        fecha_creacion=date.today(),
        grupo_investigacion=grupo,
        director=director_semillero,
        lider_estudiantil=lider_estudiantil,
        estado_aval=Semillero.EstadoAvalChoices.APROBADO,
    )


@pytest.fixture
def semillero_sin_aprobar(db, grupo, director_semillero):
    return Semillero.objects.create(
        nombre='Semillero Gamma',
        codigo='S2',
        objetivo='Pendiente de aval.',
        fecha_creacion=date.today(),
        grupo_investigacion=grupo,
        director=director_semillero,
    )  # estado_aval defaults to SIN_APROBAR


@pytest.fixture
def proyecto(db, semillero_aprobado, director_semillero, lider_estudiantil, estudiante):
    p = Proyecto.objects.create(
        titulo='Proyecto Uno',
        codigo='P1',
        descripcion='Descripción del proyecto uno.',
        objetivo_general='Objetivo general.',
        director=director_semillero,
        lider=lider_estudiantil,
    )
    p.semilleros.set([semillero_aprobado])
    p.estudiantes.set([estudiante])
    return p


@pytest.fixture
def actividad(db, proyecto, lider_estudiantil):
    return Actividad.objects.create(
        proyecto=proyecto,
        titulo='Actividad uno',
        descripcion='desc',
        responsable=lider_estudiantil,
        fecha_inicio=date.today(),
        fecha_fin=date.today(),
    )


@pytest.fixture
def cronograma_row(db, proyecto):
    return CronogramaProyecto.objects.create(
        proyecto=proyecto,
        actividad='Diseño',
        descripcion_actividad='Diseño inicial.',
        fecha_inicio=date.today(),
        fecha_fin=date.today(),
        fecha_entrega=date.today(),
    )
