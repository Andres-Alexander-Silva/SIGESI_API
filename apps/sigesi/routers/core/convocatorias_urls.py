from rest_framework.routers import DefaultRouter

from apps.sigesi.views.core.convocatoria_view import ConvocatoriaViewSet

router = DefaultRouter()
router.register(r'convocatorias', ConvocatoriaViewSet, basename='convocatorias')

urlpatterns = router.urls
