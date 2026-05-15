from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.cronograma_proyecto_view import CronogramaProyectoViewSet

router = DefaultRouter()
router.register(r'cronograma-proyecto', CronogramaProyectoViewSet, basename='cronograma-proyecto')

urlpatterns = router.urls
