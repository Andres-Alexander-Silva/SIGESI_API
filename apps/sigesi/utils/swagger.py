"""Organización modular de la documentación OpenAPI (drf-yasg).

Centraliza la taxonomía de *tags* de Swagger/ReDoc y aporta dos enganches a
drf-yasg:

- :class:`SigesiAutoSchema` permite etiquetar un ``ViewSet`` completo con un
  atributo de clase ``swagger_tags`` (sin decorar método por método), sin dejar
  de respetar los ``@swagger_auto_schema(tags=[...])`` ya existentes.
- :class:`SigesiSchemaGenerator` inyecta en el esquema raíz el arreglo ``tags``
  **ordenado por módulo** (define el orden de las secciones en Swagger UI) y la
  extensión ``x-tagGroups`` (encabezados de módulo colapsables en ReDoc).

Para mover un recurso de módulo o renombrar un tag, edite únicamente
:data:`TAG_GROUPS` (y opcionalmente :data:`TAG_DESCRIPTIONS`): es la única fuente
de verdad. El nombre del tag debe coincidir exactamente con el que emite la
vista (vía ``tags=[...]`` o ``swagger_tags``).
"""

from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.inspectors import SwaggerAutoSchema

# ---------------------------------------------------------------------------
# Taxonomía: orden de los módulos y de los recursos dentro de cada módulo.
# ---------------------------------------------------------------------------

TAG_GROUPS = [
    ('Autenticación', [
        'Autenticación',
    ]),
    ('Configuración del sistema', [
        'Usuarios',
        'RBAC · Menús',
        'RBAC · Opciones',
        'RBAC · Permisos',
        'Auditoría',
    ]),
    ('Estructura organizativa', [
        'Programas Académicos',
        'Grupos de Investigación',
        'Líneas de Investigación',
        'Semilleros',
        'Inscripciones',
    ]),
    ('Proyectos', [
        'Proyectos',
        'Actividades',
        'Cronograma de Proyecto',
        'Evidencias',
        'Evaluación de Proyectos',
    ]),
    ('Planeación estratégica', [
        'Plan Estratégico',
        'Plan de Acción',
        'Cronograma',
        'Actividad de Cronograma',
    ]),
    ('Competencias y evaluación', [
        'Competencias Investigativas',
        'Perfiles Investigativos',
        'Evaluaciones',
    ]),
    ('Producción académica', [
        'Producción Académica',
    ]),
    ('Eventos y convocatorias', [
        'Eventos',
        'Convocatorias',
        'Postulaciones',
        'Participaciones en Eventos',
    ]),
    ('Notificaciones', [
        'Notificaciones',
    ]),
    ('Dashboards e indicadores', [
        'Dashboard',
    ]),
    ('Reportes y formatos', [
        'Reportes',
        'Informes',
        'Exportar Reportes',
        'Formatos Docente',
    ]),
    ('Sistema', [
        'Estado del Servicio',
    ]),
]

# Descripción breve (en español) por tag; se muestra junto al título de la
# sección en Swagger UI / ReDoc. Puede omitirse un tag (se renderiza sin texto).
TAG_DESCRIPTIONS = {
    'Autenticación': 'Inicio de sesión, selección de rol activo, refresco de token y recuperación de contraseña.',
    'Usuarios': 'Gestión de usuarios, carga masiva y autoservicio de cuenta.',
    'RBAC · Menús': 'Menús del sistema de permisos basado en roles.',
    'RBAC · Opciones': 'Opciones (endpoints navegables) asociadas a cada menú.',
    'RBAC · Permisos': 'Permisos CRUD por rol y opción.',
    'Auditoría': 'Registro de trazabilidad institucional (solo administrador).',
    'Programas Académicos': 'Programas académicos de la institución.',
    'Grupos de Investigación': 'Grupos de investigación.',
    'Líneas de Investigación': 'Líneas de investigación.',
    'Semilleros': 'Semilleros de investigación y su aval institucional.',
    'Inscripciones': 'Matrículas de estudiantes en semilleros.',
    'Proyectos': 'Proyectos de investigación de los semilleros.',
    'Actividades': 'Actividades asociadas a los proyectos.',
    'Cronograma de Proyecto': 'Cronogramas de ejecución de cada proyecto.',
    'Evidencias': 'Evidencias (avances) documentales de los proyectos.',
    'Evaluación de Proyectos': 'Evaluaciones de los proyectos de investigación.',
    'Plan Estratégico': 'Planes estratégicos del semillero y su ciclo de aprobación.',
    'Plan de Acción': 'Planes de acción derivados del plan estratégico.',
    'Cronograma': 'Cronogramas del plan de acción.',
    'Actividad de Cronograma': 'Actividades de cada cronograma del plan de acción.',
    'Competencias Investigativas': 'Competencias investigativas y su tablero.',
    'Perfiles Investigativos': 'Perfiles investigativos de los estudiantes.',
    'Evaluaciones': 'Evaluaciones de competencias de los estudiantes (auto y heteroevaluación).',
    'Producción Académica': 'Producción académica de los semilleros.',
    'Eventos': 'Eventos académicos (catálogo administrado por el administrador).',
    'Convocatorias': 'Convocatorias asociadas a un evento.',
    'Postulaciones': 'Postulaciones de los semilleros a las convocatorias.',
    'Participaciones en Eventos': 'Participaciones de estudiantes en eventos y certificados.',
    'Notificaciones': 'Bandeja de notificaciones del usuario autenticado.',
    'Dashboard': 'Tableros de indicadores, métricas y producción académica.',
    'Reportes': 'Reportes académicos y globales de semilleros.',
    'Informes': 'Generación de informes.',
    'Exportar Reportes': 'Exportación de reportes a formato XLSX.',
    'Formatos Docente': 'Descarga de formatos institucionales para docentes.',
    'Estado del Servicio': 'Endpoints de salud y disponibilidad (ping/health).',
}


def _tags_ordenados():
    """Aplana :data:`TAG_GROUPS` al arreglo raíz ``tags`` (orden de secciones).

    Devuelve una lista de objetos *Tag* de OpenAPI (``{name, description}``) en
    el orden en que deben aparecer las secciones en Swagger UI.
    """
    tags = []
    for _grupo, nombres in TAG_GROUPS:
        for nombre in nombres:
            tags.append({'name': nombre, 'description': TAG_DESCRIPTIONS.get(nombre, '')})
    return tags


def _tag_groups():
    """Construye la extensión ``x-tagGroups`` que ReDoc usa como encabezados."""
    return [{'name': grupo, 'tags': list(nombres)} for grupo, nombres in TAG_GROUPS]


class SigesiAutoSchema(SwaggerAutoSchema):
    """Auto-schema que permite etiquetar una vista entera con ``swagger_tags``.

    Prioridad para resolver los tags de una operación:

    1. ``@swagger_auto_schema(tags=[...])`` explícito en el método (overrides);
    2. atributo de clase ``swagger_tags`` en la vista;
    3. comportamiento por defecto de drf-yasg (primer segmento de la ruta).
    """

    def get_tags(self, operation_keys=None):
        """Resuelve los tags de la operación según la prioridad documentada."""
        tags = self.overrides.get('tags')
        if not tags:
            tags = getattr(self.view, 'swagger_tags', None)
        if not tags:
            tags = super().get_tags(operation_keys)
        return tags


class SigesiSchemaGenerator(OpenAPISchemaGenerator):
    """Generador que ordena las secciones por módulo y agrega ``x-tagGroups``.

    Tras delegar en drf-yasg la construcción del esquema, fija el arreglo raíz
    ``tags`` (orden de secciones en Swagger UI) e inyecta ``x-tagGroups`` (grupos
    de módulos colapsables en ReDoc).
    """

    def get_schema(self, request=None, public=False):
        """Genera el esquema y le añade el orden de tags y los grupos de módulo."""
        swagger = super().get_schema(request, public)
        swagger.tags = _tags_ordenados()
        swagger['x-tagGroups'] = _tag_groups()
        return swagger
