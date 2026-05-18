from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.produccion_academica_view import ProduccionAcademicaViewSet

router = DefaultRouter()
router.register(
    r'producciones-academicas',
    ProduccionAcademicaViewSet,
    basename='produccion-academica',
)

urlpatterns = [
    path('', include(router.urls)),
]
