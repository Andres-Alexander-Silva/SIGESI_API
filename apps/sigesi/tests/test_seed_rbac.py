"""Tests del comando de management ``seed_rbac``.

El comando inyecta los Menús/Opciones/Permisos RBAC faltantes para las rutas del
frontend. La base de prueba ya trae la siembra de la migración 0003 (6 menús,
8 opciones), así que estos tests verifican los *deltas* y no conteos absolutos.
"""
import pytest
from django.core.management import call_command

from apps.sigesi.models import Menu, Opcion, Permiso
from apps.sigesi.management.commands.seed_rbac import (
    MENUS_NUEVOS,
    OPCIONES_NUEVAS,
    PERMISOS_NUEVOS,
)


def _counts():
    return (Menu.objects.count(), Opcion.objects.count(), Permiso.objects.count())


@pytest.mark.django_db
def test_seed_rbac_crea_los_faltantes():
    """Crea exactamente los menús, opciones y permisos nuevos declarados."""
    m0, o0, p0 = _counts()

    call_command('seed_rbac')

    m1, o1, p1 = _counts()
    assert m1 - m0 == len(MENUS_NUEVOS)
    assert o1 - o0 == len(OPCIONES_NUEVAS)
    assert p1 - p0 == len(PERMISOS_NUEVOS)


@pytest.mark.django_db
def test_seed_rbac_es_idempotente():
    """Re-ejecutar no crea duplicados."""
    call_command('seed_rbac')
    snapshot = _counts()

    call_command('seed_rbac')
    assert _counts() == snapshot


@pytest.mark.django_db
def test_dry_run_no_persiste_nada():
    """``--dry-run`` revierte la transacción: la BD no cambia."""
    antes = _counts()
    call_command('seed_rbac', '--dry-run')
    assert _counts() == antes


@pytest.mark.django_db
def test_opciones_usan_la_ruta_del_frontend():
    """Las opciones se crean con la URL = ruta real del frontend."""
    call_command('seed_rbac')
    for _menu, _nombre, url in OPCIONES_NUEVAS:
        assert Opcion.objects.filter(url=url).exists(), f'falta opción {url}'

    # Las 3 rutas con desajuste can()/ruta se siembran con la RUTA, no el can().
    assert Opcion.objects.filter(url='/produccion_academica').exists()
    assert not Opcion.objects.filter(url='/produccion').exists()
    assert Opcion.objects.filter(url='/evaluaciones_proyecto').exists()
    assert not Opcion.objects.filter(url='/evaluaciones-proyecto').exists()


@pytest.mark.django_db
def test_matriz_de_permisos_representativa():
    """Verifica algunos flags clave inferidos del backend."""
    call_command('seed_rbac')

    # Administrador: CRUD total sobre /proyectos.
    admin_proy = Permiso.objects.get(opcion__url='/proyectos', rol='administrador')
    assert (admin_proy.puede_consultar, admin_proy.puede_crear,
            admin_proy.puede_actualizar, admin_proy.puede_eliminar) == (True, True, True, True)

    # Estudiante: lectura sin borrado en /proyectos.
    est_proy = Permiso.objects.get(opcion__url='/proyectos', rol='estudiante')
    assert est_proy.puede_consultar is True
    assert est_proy.puede_eliminar is False

    # lider_estudiantil es solo-lectura en /evaluaciones_proyecto.
    le_eval = Permiso.objects.get(opcion__url='/evaluaciones_proyecto', rol='lider_estudiantil')
    assert le_eval.puede_consultar is True
    assert le_eval.puede_crear is False
    assert le_eval.puede_actualizar is False

    # /auditoria solo tiene fila para administrador (los demás roles no la ven).
    roles_auditoria = set(
        Permiso.objects.filter(opcion__url='/auditoria').values_list('rol', flat=True)
    )
    assert roles_auditoria == {'administrador'}

    # Director de Semillero: actualizar pero no crear/eliminar en competencias.
    ds_comp = Permiso.objects.get(
        opcion__url='/competencias_investigativas', rol='director_semillero'
    )
    assert ds_comp.puede_actualizar is True
    assert ds_comp.puede_crear is False
    assert ds_comp.puede_eliminar is False
