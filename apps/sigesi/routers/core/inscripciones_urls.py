from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.inscripcion_view import InscripcionViewSet

router = DefaultRouter()
router.register(r'inscripciones', InscripcionViewSet, basename='inscripcion')

urlpatterns = [
    path('', include(router.urls)),
]
