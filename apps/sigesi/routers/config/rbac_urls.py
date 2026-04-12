from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.sigesi.views.config.rbac_view import MenuViewSet, OpcionViewSet, PermisoViewSet

# Usamos DefaultRouter de DRF para generar automáticamente las sub-rutas CRUD
router = DefaultRouter()
router.register(r'menus', MenuViewSet, basename='menu')
router.register(r'opciones', OpcionViewSet, basename='opcion')
router.register(r'permisos', PermisoViewSet, basename='permiso')

urlpatterns = router.urls
