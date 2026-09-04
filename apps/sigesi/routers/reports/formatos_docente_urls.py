from django.urls import path

from apps.sigesi.views.reports.formatos_docente_view import FormulariosDocenteBulkView


urlpatterns = [
    path('formularios-docente/', FormulariosDocenteBulkView.as_view(),
         name='formularios-docente'),
]
