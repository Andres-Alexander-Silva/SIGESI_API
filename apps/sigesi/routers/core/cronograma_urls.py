from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.cronograma_view import CronogramaViewSet

router = DefaultRouter()
router.register(r'cronograma', CronogramaViewSet, basename='cronograma')

urlpatterns = router.urls
