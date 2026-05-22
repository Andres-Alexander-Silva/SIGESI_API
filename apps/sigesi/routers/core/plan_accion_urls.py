from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.plan_accion_view import PlanAccionViewSet

router = DefaultRouter()
router.register(r'plan-accion', PlanAccionViewSet, basename='plan-accion')

urlpatterns = router.urls
