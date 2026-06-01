from rest_framework.routers import DefaultRouter

from apps.sigesi.views.core.participacion_evento_view import ParticipacionEventoViewSet

router = DefaultRouter()
router.register(r'participaciones-evento', ParticipacionEventoViewSet,
                basename='participaciones-evento')

urlpatterns = router.urls
