from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.evidencia_view import EvidenciaViewSet

router = DefaultRouter()
router.register(r'avances', EvidenciaViewSet, basename='avances')

urlpatterns = router.urls
