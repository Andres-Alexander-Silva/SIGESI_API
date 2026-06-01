from rest_framework.routers import DefaultRouter

from apps.sigesi.views.core.postulacion_view import PostulacionViewSet

router = DefaultRouter()
router.register(r'postulaciones', PostulacionViewSet, basename='postulaciones')

urlpatterns = router.urls
