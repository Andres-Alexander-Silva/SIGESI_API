from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.evaluacion_proyecto_view import EvaluacionProyectoViewSet

router = DefaultRouter()
router.register(r'evaluaciones', EvaluacionProyectoViewSet, basename='evaluaciones-proyecto')

urlpatterns = [
    path('', include(router.urls)),
]
