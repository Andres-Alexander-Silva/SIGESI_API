"""ViewSet de solo lectura de la traza de auditoría (solo administrador)."""
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import RegistroAuditoria
from apps.sigesi.decorators.permissions import AuditoriaPermission
from apps.sigesi.serializers.config.auditoria_serializer import (
    RegistroAuditoriaSerializer,
)


class RegistroAuditoriaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Consulta de la traza histórica institucional (solo lectura, solo-admin).

    - Las filas las crea automáticamente el ``AuditoriaMiddleware``; este
      endpoint **no** permite crear, editar ni eliminar.
    - Acceso restringido al rol administrador (``AuditoriaPermission``).
    - Soporta filtros ``?accion=&modulo=&usuario_email=&rol_activo=``.
    - La respuesta usa el sobre ``{success, data}``.
    """

    serializer_class = RegistroAuditoriaSerializer
    permission_classes = [AuditoriaPermission]
    filterset_fields = ['accion', 'modulo', 'usuario_email', 'rol_activo']

    def get_queryset(self):
        """Traza completa, ordenada por fecha descendente (Meta del modelo)."""
        if getattr(self, 'swagger_fake_view', False):
            return RegistroAuditoria.objects.none()
        return RegistroAuditoria.objects.select_related('usuario').all()

    @swagger_auto_schema(
        operation_summary='Listar registros de auditoría',
        operation_description=(
            'Devuelve la traza histórica de actividad institucional. '
            'Solo accesible para el administrador.'
        ),
        manual_parameters=[
            openapi.Parameter('accion', openapi.IN_QUERY,
                              description='Filtrar por acción.',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('modulo', openapi.IN_QUERY,
                              description='Filtrar por módulo.',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('usuario_email', openapi.IN_QUERY,
                              description='Filtrar por correo del usuario.',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('rol_activo', openapi.IN_QUERY,
                              description='Filtrar por rol activo.',
                              type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: RegistroAuditoriaSerializer(many=True), 403: 'Solo admin'},
        tags=['Auditoría'],
    )
    def list(self, request, *args, **kwargs):
        """Lista la traza de auditoría envuelta en ``{success, data}``."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated = self.get_paginated_response(serializer.data)
            paginated.data = {'success': True, 'data': paginated.data}
            return paginated
        serializer = self.get_serializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})

    @swagger_auto_schema(
        operation_summary='Detalle de un registro de auditoría',
        responses={200: RegistroAuditoriaSerializer, 403: 'Solo admin',
                   404: 'No encontrado'},
        tags=['Auditoría'],
    )
    def retrieve(self, request, *args, **kwargs):
        """Devuelve un registro de auditoría envuelto en ``{success, data}``."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({'success': True, 'data': serializer.data})
