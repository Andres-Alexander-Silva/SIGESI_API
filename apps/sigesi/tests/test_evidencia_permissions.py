"""Matriz de permisos de EvidenciaPermission (HU-021, fase F6).

`EvidenciaPermission` estaba duplicada — una versión activa en
`views/core/evidencia_view.py` y una más estricta (`EvidenciaRolePermission`,
sin uso) en `decorators/permissions.py`. Se consolidó en el segundo módulo
conservando el comportamiento ACTIVO (ver docs/HU-021_PLAN_IMPLEMENTACION.md,
hallazgo H6): este archivo fija ese comportamiento con pruebas explícitas,
incluido el caso que quedaba ambiguo — un estudiante miembro del proyecto
pero que no es responsable de la actividad ni subió el archivo.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.sigesi.models import Evidencia

URL = '/api/v1/core/avances/'


def _pdf(name='evidencia.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 fake content', content_type='application/pdf')


@pytest.fixture
def evidencia_de_otro_estudiante(db, actividad, otro_estudiante, proyecto):
    """Evidencia subida por un estudiante que NO es el responsable de la
    actividad ni el director/líder del proyecto — el caso ambiguo."""
    proyecto.estudiantes.add(otro_estudiante)
    return Evidencia.objects.create(
        actividad=actividad, tipo='documento', titulo='t', descripcion='d',
        archivo=_pdf(), subido_por=otro_estudiante,
    )


@pytest.mark.django_db
def test_estudiante_miembro_no_ve_evidencia_de_un_companero_no_responsable(
    auth_client, estudiante, proyecto, evidencia_de_otro_estudiante,
):
    """Ambos son estudiantes del mismo proyecto; ninguno es responsable de la
    actividad ni director/líder — `subido_por` es la única puerta."""
    proyecto.estudiantes.add(estudiante)
    client = auth_client(estudiante)
    resp = client.get(f'{URL}{evidencia_de_otro_estudiante.id}/')
    assert resp.status_code == 404  # fuera del queryset filtrado por get_queryset()


@pytest.mark.django_db
def test_estudiante_no_puede_editar_evidencia_de_un_companero(
    auth_client, estudiante, proyecto, evidencia_de_otro_estudiante,
):
    proyecto.estudiantes.add(estudiante)
    client = auth_client(estudiante)
    resp = client.patch(
        f'{URL}{evidencia_de_otro_estudiante.id}/',
        {'titulo': 'Intento de edición'},
        format='json',
    )
    assert resp.status_code in (403, 404)


@pytest.mark.django_db
def test_responsable_de_la_actividad_puede_editar_su_evidencia(
    auth_client, lider_estudiantil, actividad,
):
    """`actividad.responsable == lider_estudiantil` (fixture de conftest)."""
    ev = Evidencia.objects.create(
        actividad=actividad, tipo='documento', titulo='t', descripcion='d',
        archivo=_pdf(), subido_por=lider_estudiantil,
    )
    client = auth_client(lider_estudiantil)
    resp = client.patch(f'{URL}{ev.id}/', {'titulo': 'Actualizado'}, format='json')
    assert resp.status_code == 200, resp.content


@pytest.mark.django_db
def test_director_del_proyecto_puede_ver_evidencia_de_cualquier_miembro(
    auth_client, director_semillero, proyecto, evidencia_de_otro_estudiante,
):
    """`proyecto.director == director_semillero` (fixture de conftest)."""
    client = auth_client(director_semillero)
    resp = client.get(f'{URL}{evidencia_de_otro_estudiante.id}/')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_administrador_ve_y_edita_cualquier_evidencia(
    auth_client, admin_user, evidencia_de_otro_estudiante,
):
    client = auth_client(admin_user)
    resp = client.get(f'{URL}{evidencia_de_otro_estudiante.id}/')
    assert resp.status_code == 200

    resp = client.patch(
        f'{URL}{evidencia_de_otro_estudiante.id}/',
        {'titulo': 'Editado por admin'},
        format='json',
    )
    assert resp.status_code == 200, resp.content
