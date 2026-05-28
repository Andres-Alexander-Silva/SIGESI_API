from rest_framework.routers import DefaultRouter
from apps.sigesi.views.core.competencia_investigativa_view import CompetenciaInvestigativaViewSet

router = DefaultRouter()
router.register(
    r'competencias-investigativas',
    CompetenciaInvestigativaViewSet,
    basename='competencias-investigativas',
)

urlpatterns = router.urls
