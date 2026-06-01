from rest_framework.routers import DefaultRouter

from apps.sigesi.views.core.notificacion_view import NotificacionViewSet

router = DefaultRouter()
router.register(r'notificaciones', NotificacionViewSet, basename='notificaciones')

urlpatterns = router.urls
