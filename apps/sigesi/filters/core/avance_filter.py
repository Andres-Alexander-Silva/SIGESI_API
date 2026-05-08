import django_filters
from apps.sigesi.models import Avance


class AvanceFilter(django_filters.FilterSet):
    """
    Filtros para el listado de Avances.

    Soporta:
      - proyecto:   ID del proyecto (igualdad exacta)
      - estado:     Estado del avance (iexact)
      - fecha_desde / fecha_hasta: rango de fechas
      - registrado_por: ID del usuario que registró el avance
    """
    proyecto        = django_filters.NumberFilter(field_name='proyecto__id')
    estado          = django_filters.CharFilter(lookup_expr='iexact')
    fecha_desde     = django_filters.DateFilter(field_name='fecha', lookup_expr='gte')
    fecha_hasta     = django_filters.DateFilter(field_name='fecha', lookup_expr='lte')
    registrado_por  = django_filters.NumberFilter(field_name='registrado_por__id')

    class Meta:
        model  = Avance
        fields = ['proyecto', 'estado', 'fecha_desde', 'fecha_hasta', 'registrado_por']
