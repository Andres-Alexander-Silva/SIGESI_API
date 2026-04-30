import django_filters
from apps.sigesi.models import User


class UserFilter(django_filters.FilterSet):
    """
    FilterSet para el endpoint GET /api/users/.

    Filtros activos:
      - rol: filtra por rol exacto (ej: ?rol=estudiante)

    Filtros futuros sugeridos (agregar en este mismo archivo):
      - is_active       → filtrar por estado activo/inactivo (ej: ?is_active=true)
      - programa_academico → filtrar por programa (ej: ?programa_academico=1)
      - search          → búsqueda parcial por nombre/email (via SearchFilter en el ViewSet)
      - created_at__gte / created_at__lte → filtrar por rango de fechas
    """
    rol = django_filters.ChoiceFilter(choices=User.RolChoices.choices, method='filter_by_rol')

    class Meta:
        model  = User
        fields = ['rol']

    def filter_by_rol(self, queryset, name, value):
        """Filtra el ArrayField 'roles' para comprobar si contiene el valor dado."""
        return queryset.filter(roles__contains=[value])
