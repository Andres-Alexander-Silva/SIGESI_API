import django_filters
from apps.sigesi.models import LineaInvestigacion

class LineaInvestigacionFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(lookup_expr='icontains')
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = LineaInvestigacion
        fields = ['nombre', 'is_active']
