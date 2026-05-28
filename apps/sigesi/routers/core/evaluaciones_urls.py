from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.evaluacion_view import EvaluacionViewSet

router = DefaultRouter()
router.register(
    r'evaluaciones',
    EvaluacionViewSet,
    basename='evaluaciones',
)

urlpatterns = router.urls
