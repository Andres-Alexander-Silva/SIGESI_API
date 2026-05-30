from django.urls import path

from apps.sigesi.views.reports.formatos_docente_view import (
    FormulariosDocenteBulkView,
    FormularioDocenteDetailView,
)


urlpatterns = [
    path('formularios-docente/', FormulariosDocenteBulkView.as_view(),
         name='formularios-docente'),
    path('formularios-docente/descargar/', FormularioDocenteDetailView.as_view(),
         name='formulario-docente-detail'),
]
