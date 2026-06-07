"""Regresión: los endpoints de reportes/informes ya no caen para no-admins.

Antes, ``informe_view`` y ``reportes_view`` referenciaban dos roles inexistentes
(``RolChoices.DOCENTE`` y ``RolChoices.DIRECTOR_PROGRAMA``), por lo que cualquier
usuario no administrador disparaba ``AttributeError`` → 500 al evaluar el scope.
Tras la corrección (``DOCENTE`` → ``DIRECTOR_SEMILLERO``, ``DIRECTOR_PROGRAMA`` →
``ADMINISTRADOR``) un director debe poder consultar estos endpoints (200).
"""
import pytest

URL_INFORMES = '/api/v1/reportes/'
URL_REPORTE_SEMILLEROS = '/api/v1/reportes/semilleros/'
URL_REPORTE_PROYECTOS = '/api/v1/reportes/proyectos/'


@pytest.mark.django_db
@pytest.mark.parametrize('url', [
    URL_INFORMES,
    URL_REPORTE_SEMILLEROS,
    URL_REPORTE_PROYECTOS,
])
def test_director_semillero_consulta_reportes_sin_500(url, auth_client, director_semillero):
    """Un director de semillero obtiene 200 (no 500) en los endpoints de reportes."""
    resp = auth_client(director_semillero).get(url)
    assert resp.status_code == 200, resp.content[:300]


@pytest.mark.django_db
@pytest.mark.parametrize('url', [
    URL_INFORMES,
    URL_REPORTE_SEMILLEROS,
    URL_REPORTE_PROYECTOS,
])
def test_director_grupo_consulta_reportes_sin_500(url, auth_client, director_grupo):
    """Un director de grupo obtiene 200 (no 500) en los endpoints de reportes."""
    resp = auth_client(director_grupo).get(url)
    assert resp.status_code == 200, resp.content[:300]
