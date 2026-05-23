from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.plan_estrategico_view import PlanEstrategicoViewSet

router = DefaultRouter()
router.register(r'plan-estrategico', PlanEstrategicoViewSet, basename='plan-estrategico')

urlpatterns = router.urls
