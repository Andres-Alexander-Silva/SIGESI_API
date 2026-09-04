from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.sigesi.views.reports.formato_institucional_view import FormatoInstitucionalViewSet

router = DefaultRouter()
router.register(
    r'formatos-institucionales',
    FormatoInstitucionalViewSet,
    basename='formato-institucional',
)

urlpatterns = [
    path('', include(router.urls)),
]
