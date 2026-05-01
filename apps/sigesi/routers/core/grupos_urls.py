from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.grupo_investigacion_view import GrupoInvestigacionViewSet

router = DefaultRouter()
router.register(r'grupos-investigacion', GrupoInvestigacionViewSet, basename='grupo-investigacion')

urlpatterns = [
    path('', include(router.urls)),
]
