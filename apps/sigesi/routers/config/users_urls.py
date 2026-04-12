from rest_framework.routers import DefaultRouter
from apps.sigesi.views.config.user_view import UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')

urlpatterns = router.urls
