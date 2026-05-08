import django_filters
from apps.sigesi.models import Avance


class AvanceFilter(django_filters.FilterSet):
    """
    Filtros para el listado de Avances.

    Parámetros canónicos (especificación del user story):
      - proyecto_id   → ID del proyecto  (GET /avances?proyecto_id=<id>)
      - usuario_id    → ID del registrador (GET /avances?proyecto_id=<id>&usuario_id=<id>)

    Parámetros extendidos / backward-compatible:
      - proyecto      → alias de proyecto_id
      - registrado_por→ alias de usuario_id
      - estado        → filtra por estado del avance (iexact)
      - fecha_desde   → avances desde esta fecha (YYYY-MM-DD)
      - fecha_hasta   → avances hasta esta fecha  (YYYY-MM-DD)

    NOTA: La validación de existencia y pertenencia del usuario al proyecto
    se realiza en la vista (AvanceViewSet.list) para poder retornar los
    códigos HTTP apropiados (404, 400, 403) con mensajes descriptivos.
    """

    # ── Canónicos (user story) ──────────────────────────────────────
    proyecto_id  = django_filters.NumberFilter(field_name='proyecto__id')
    usuario_id   = django_filters.NumberFilter(field_name='registrado_por__id')

    # ── Backward-compatible / adicionales ──────────────────────────
    proyecto       = django_filters.NumberFilter(field_name='proyecto__id')
    registrado_por = django_filters.NumberFilter(field_name='registrado_por__id')
    estado         = django_filters.CharFilter(lookup_expr='iexact')
    fecha_desde    = django_filters.DateFilter(field_name='fecha', lookup_expr='gte')
    fecha_hasta    = django_filters.DateFilter(field_name='fecha', lookup_expr='lte')

    class Meta:
        model  = Avance
        fields = [
            'proyecto_id', 'usuario_id',
            'proyecto', 'registrado_por',
            'estado', 'fecha_desde', 'fecha_hasta',
        ]
