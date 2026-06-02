"""URLs para el dashboard de indicadores."""
from django.urls import path
from apps.sigesi.views.core.indicadores_dashboard_view import (
    IndicadoresDashboardView,
)

urlpatterns = [
    path(
        'dashboard/indicadores/',
        IndicadoresDashboardView.as_view(),
        name='indicadores-dashboard',
    ),
]