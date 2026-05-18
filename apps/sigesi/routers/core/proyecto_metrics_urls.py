from django.urls import path
from apps.sigesi.views.core.proyecto_metrics_view import ProyectoMetricsDashboardView

urlpatterns = [
    path(
        'proyectos/metricas-dashboard/',
        ProyectoMetricsDashboardView.as_view(),
        name='proyecto-metricas-dashboard',
    ),
]
