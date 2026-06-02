"""URLs para el dashboard de producción académica."""
from django.urls import path
from apps.sigesi.views.core.produccion_academica_dashboard_view import (
    ProduccionAcademicaDashboardView,
)

urlpatterns = [
    path(
        'produccion-academica/dashboard/',
        ProduccionAcademicaDashboardView.as_view(),
        name='produccion-academica-dashboard',
    ),
]