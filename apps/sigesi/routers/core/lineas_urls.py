from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.linea_investigacion_view import LineaInvestigacionViewSet

router = DefaultRouter()
router.register(r'lineas-investigacion', LineaInvestigacionViewSet, basename='linea-investigacion')

urlpatterns = [
    path('', include(router.urls)),
]
