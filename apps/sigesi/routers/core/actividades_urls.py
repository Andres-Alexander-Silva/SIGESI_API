from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.actividad_view import ActividadViewSet

router = DefaultRouter()
router.register(r'actividades', ActividadViewSet, basename='actividades')

urlpatterns = router.urls
