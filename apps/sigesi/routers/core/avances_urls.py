from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.avance_view import AvanceViewSet

router = DefaultRouter()
router.register(r'avances', AvanceViewSet, basename='avances')

urlpatterns = router.urls
