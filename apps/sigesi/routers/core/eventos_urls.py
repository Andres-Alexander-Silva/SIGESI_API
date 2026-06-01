from rest_framework.routers import DefaultRouter

from apps.sigesi.views.core.evento_view import EventoViewSet

router = DefaultRouter()
router.register(r'eventos', EventoViewSet, basename='eventos')

urlpatterns = router.urls
