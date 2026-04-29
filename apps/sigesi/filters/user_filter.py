import django_filters
from apps.sigesi.models import User


class UserFilter(django_filters.FilterSet):
    """
    FilterSet para el endpoint GET /api/users/.

    Filtros activos:
      - (ninguno aún — la infraestructura está lista para extenderse)

    Filtros futuros sugeridos (agregar en este mismo archivo):
      - rol             → filtrar por rol exacto (ej: ?rol=estudiante)
      - is_active       → filtrar por estado activo/inactivo (ej: ?is_active=true)
      - programa_academico → filtrar por programa (ej: ?programa_academico=1)
      - search          → búsqueda parcial por nombre/email (via SearchFilter en el ViewSet)
      - created_at__gte / created_at__lte → filtrar por rango de fechas

    Ejemplo de filtro futuro:
        rol = django_filters.ChoiceFilter(choices=User.RolChoices.choices)
        is_active = django_filters.BooleanFilter()
    """

    class Meta:
        model  = User
        fields = []   # se irán incorporando aquí los filtros futuros
