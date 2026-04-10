from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Semilleros de Investigación API",
        default_version='v1',
        description="API para la Plataforma Estratégica de Gestión y Fortalecimiento de Semilleros de Investigación",
        contact=openapi.Contact(email="admin@semilleros.com"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # Admin
    path('panel_admin_sigesi_api/', admin.site.urls),
    # Health & Ping
    path('api/v1/', include('apps.sigesi.routers.health')),
    # Auth
    path('api/v1/auth/', include('apps.sigesi.routers.auth.auth_urls')),
    # Apps
    # path('api/v1/users/', include('apps.users.urls')),
    # Swagger / Documentación
    path('swagger/', schema_view.with_ui('swagger',
         cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc',
         cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
