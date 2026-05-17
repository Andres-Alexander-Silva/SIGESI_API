from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.programa_academico_view import ProgramaAcademicoViewSet

router = DefaultRouter()
router.register(r'programas-academicos', ProgramaAcademicoViewSet, basename='programa-academico')

urlpatterns = [
    path('', include(router.urls)),
]
