from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.sigesi.views.config.semillero_view import SemilleroViewSet

router = DefaultRouter()
router.register(r'semilleros', SemilleroViewSet, basename='semillero')

urlpatterns = [
    path('', include(router.urls)),
]
