import django_filters
from apps.sigesi.models import GrupoInvestigacion

class GrupoInvestigacionFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(lookup_expr='icontains')
    codigo = django_filters.CharFilter(lookup_expr='iexact')
    is_active = django_filters.BooleanFilter()
    programa_academico = django_filters.NumberFilter(field_name='programa_academico__id')
    director = django_filters.NumberFilter(field_name='director__id')

    class Meta:
        model = GrupoInvestigacion
        fields = ['nombre', 'codigo', 'is_active', 'programa_academico', 'director']
