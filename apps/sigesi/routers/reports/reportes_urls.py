from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.sigesi.views.reports.reportes_view import ReporteAcademicoProyectoList, ReporteGlobalSemilleroList
from apps.sigesi.views.reports.informe_view import InformeViewSet

router = DefaultRouter()
router.register(r'', InformeViewSet, basename='informes')

urlpatterns = [
    path('proyectos/', ReporteAcademicoProyectoList.as_view(), name='reporte-proyectos'),
    path('semilleros/', ReporteGlobalSemilleroList.as_view(), name='reporte-semilleros'),
    path('', include(router.urls)),
]
