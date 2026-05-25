from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.actividad_cronograma_view import ActividadCronogramaViewSet

router = DefaultRouter()
router.register(r'actividad-cronograma', ActividadCronogramaViewSet,
                basename='actividad-cronograma')

urlpatterns = router.urls
