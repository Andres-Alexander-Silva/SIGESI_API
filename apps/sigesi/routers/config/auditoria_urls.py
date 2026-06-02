"""URLs de la traza de auditoría (solo lectura, solo-admin)."""
from rest_framework.routers import DefaultRouter

from apps.sigesi.views.config.auditoria_view import RegistroAuditoriaViewSet

router = DefaultRouter()
router.register(r'auditoria/logs', RegistroAuditoriaViewSet,
                basename='auditoria-logs')

urlpatterns = router.urls
