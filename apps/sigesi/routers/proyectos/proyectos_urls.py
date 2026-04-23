from rest_framework.routers import DefaultRouter
from apps.sigesi.views.proyectos.proyecto_view import ProyectoViewSet

router = DefaultRouter()
router.register(r'', ProyectoViewSet, basename='proyecto')

urlpatterns = router.urls
