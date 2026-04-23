from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.proyecto_view import ProyectoViewSet

router = DefaultRouter()
router.register(r'proyectos', ProyectoViewSet, basename='proyectos')

urlpatterns = router.urls
