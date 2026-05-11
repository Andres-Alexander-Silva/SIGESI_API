import django_filters
from apps.sigesi.models import ProyectoEstudiante

class ProyectoEstudianteFilter(django_filters.FilterSet):
    """
    Filtros para el listado de participaciones de estudiantes en proyectos.

    Soporta:
      - proyecto_id:   ID del proyecto
      - estudiante_id: ID del estudiante participante
      - semillero_id:  ID de un semillero (filtra proyectos asociados a este semillero)
      - rol:           Rol en el proyecto (ej: 'investigador', 'auxiliar')
      - estado:        Estado de participación ('activo', 'inactivo')
    """
    proyecto_id   = django_filters.NumberFilter(field_name='proyecto__id')
    estudiante_id = django_filters.NumberFilter(field_name='estudiante__id')
    semillero_id  = django_filters.NumberFilter(field_name='proyecto__semilleros__id', distinct=True)
    rol           = django_filters.CharFilter(field_name='rol_en_proyecto', lookup_expr='iexact')
    estado        = django_filters.CharFilter(field_name='estado_participacion', lookup_expr='iexact')

    class Meta:
        model  = ProyectoEstudiante
        fields = ['proyecto_id', 'estudiante_id', 'semillero_id', 'rol', 'estado']
