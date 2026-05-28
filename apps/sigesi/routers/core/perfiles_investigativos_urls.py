from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.perfil_investigativo_view import PerfilInvestigativoViewSet

router = DefaultRouter()
router.register(
    r'perfiles-investigativos',
    PerfilInvestigativoViewSet,
    basename='perfiles-investigativos',
)

urlpatterns = router.urls
