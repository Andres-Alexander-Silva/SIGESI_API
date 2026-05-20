from django.urls import path

from apps.sigesi.views.reports.export_view import (
    ExportEstudiantesView,
    ExportProyectosView,
    ExportAvancesView,
    ExportProduccionesAcademicasView,
    ExportActividadesView,
    ExportIndicadoresView,
)


urlpatterns = [
    path('estudiantes/', ExportEstudiantesView.as_view(), name='export-estudiantes'),
    path('proyectos/', ExportProyectosView.as_view(), name='export-proyectos'),
    path('avances/', ExportAvancesView.as_view(), name='export-avances'),
    path('producciones-academicas/', ExportProduccionesAcademicasView.as_view(),
         name='export-producciones-academicas'),
    path('actividades/', ExportActividadesView.as_view(), name='export-actividades'),
    path('indicadores/', ExportIndicadoresView.as_view(), name='export-indicadores'),
]
