from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.proyecto_estudiante_view import ProyectoEstudianteViewSet

router = DefaultRouter()
router.register(r'proyectos-estudiantes', ProyectoEstudianteViewSet, basename='proyectos-estudiantes')

urlpatterns = router.urls
