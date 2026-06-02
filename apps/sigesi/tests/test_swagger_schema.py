"""Verifica la organización modular de la documentación OpenAPI (drf-yasg).

Genera el esquema en proceso con :class:`SigesiSchemaGenerator` y comprueba que:
- el arreglo raíz ``tags`` respeta el orden modular de ``TAG_GROUPS``;
- ``x-tagGroups`` refleja exactamente la agrupación por módulo;
- toda operación está etiquetada con un tag de la taxonomía (ninguna cae en el
  tag por defecto basado en la ruta);
- no quedan tags heredados (``Core - ``, ``RBAC - ``, ``Auth``);
- los recursos antes sin etiqueta quedaron cubiertos;
- cada tag declarado en la taxonomía se usa al menos una vez.
"""
import pytest
from drf_yasg import openapi

from apps.sigesi.utils.swagger import SigesiSchemaGenerator, TAG_GROUPS

HTTP_METHODS = ('get', 'post', 'put', 'patch', 'delete')

# Orden plano esperado de los tags y conjunto total de la taxonomía.
TAGS_ORDENADOS = [t for _grupo, nombres in TAG_GROUPS for t in nombres]
TAGS_TAXONOMIA = set(TAGS_ORDENADOS)


@pytest.fixture(scope='module')
def swagger():
    """Esquema OpenAPI generado por el generador modular del proyecto."""
    generator = SigesiSchemaGenerator(
        openapi.Info(title='SIGESI API (test)', default_version='v1'),
        url='',
    )
    return generator.get_schema(request=None, public=True)


def _operaciones(swagger):
    """Itera ``(ruta, método, operación)`` sobre todas las rutas del esquema."""
    for ruta, path_item in swagger['paths'].items():
        for metodo in HTTP_METHODS:
            operacion = path_item.get(metodo)
            if operacion is not None:
                yield ruta, metodo, operacion


def _tags_usados(swagger):
    """Conjunto de todos los tags efectivamente aplicados a alguna operación."""
    usados = set()
    for _ruta, _metodo, operacion in _operaciones(swagger):
        usados.update(operacion.get('tags', []))
    return usados


def test_tags_raiz_en_orden_modular(swagger):
    nombres = [t['name'] for t in swagger['tags']]
    assert nombres == TAGS_ORDENADOS


def test_x_tag_groups_refleja_la_taxonomia(swagger):
    grupos = swagger['x-tagGroups']
    esperado = [{'name': g, 'tags': list(ts)} for g, ts in TAG_GROUPS]
    assert grupos == esperado


def test_toda_operacion_esta_en_la_taxonomia(swagger):
    fuera = []
    for ruta, metodo, operacion in _operaciones(swagger):
        tags = set(operacion.get('tags', []))
        if not tags or not tags.issubset(TAGS_TAXONOMIA):
            fuera.append((metodo.upper(), ruta, sorted(tags)))
    assert not fuera, f'Operaciones con tags fuera de la taxonomía: {fuera}'


def test_no_quedan_tags_heredados(swagger):
    for tag in _tags_usados(swagger):
        assert not tag.startswith('Core - '), tag
        assert not tag.startswith('RBAC - '), tag
        assert tag != 'Auth', 'El tag "Auth" debió renombrarse a "Autenticación".'


@pytest.mark.parametrize('tag', [
    'Evidencias',
    'Evaluación de Proyectos',
    'Informes',
    'Reportes',
    'Estado del Servicio',
])
def test_recursos_antes_sin_etiqueta_cubiertos(swagger, tag):
    assert tag in _tags_usados(swagger)


def test_cada_tag_de_la_taxonomia_se_usa(swagger):
    usados = _tags_usados(swagger)
    sin_uso = [t for t in TAGS_ORDENADOS if t not in usados]
    assert not sin_uso, f'Tags declarados en la taxonomía pero sin operaciones: {sin_uso}'
