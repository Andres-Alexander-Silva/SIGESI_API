"""ViewSet de la bandeja personal de notificaciones."""
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import Notificacion
from apps.sigesi.serializers.core.notificacion_serializer import (
    NotificacionListSerializer,
)


class NotificacionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Bandeja personal de notificaciones (solo lectura, marcar leídas, eliminar).

    - Solo el propio destinatario ve sus notificaciones (``get_queryset``).
    - Las notificaciones se crean automáticamente desde los viewsets del flujo
      académico (Convocatoria / Postulación / ParticipaciónEvento); este
      endpoint **no** permite crear.
    - Acciones: ``marcar-leida`` (una) y ``marcar-todas-leidas`` (bulk).
    """

    serializer_class = NotificacionListSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['leida', 'tipo']
    http_method_names = ['get', 'delete', 'patch', 'head', 'options']

    def get_queryset(self):
        """Restringe al usuario autenticado (no se exponen otras bandejas)."""
        return (
            Notificacion.objects
            .filter(usuario=self.request.user)
            .select_related('content_type')
        )

    @swagger_auto_schema(
        operation_summary='Listar mis notificaciones',
        manual_parameters=[
            openapi.Parameter('leida', openapi.IN_QUERY,
                              description='Filtrar por leídas/no leídas.',
                              type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter('tipo', openapi.IN_QUERY,
                              description='Filtrar por tipo de notificación.',
                              type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: NotificacionListSerializer(many=True)},
        tags=['Notificaciones'],
    )
    def list(self, request, *args, **kwargs):
        """Lista las notificaciones del usuario autenticado."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Detalle de una notificación',
        responses={200: NotificacionListSerializer, 404: 'No encontrada'},
        tags=['Notificaciones'],
    )
    def retrieve(self, request, *args, **kwargs):
        """Devuelve el detalle de una notificación propia."""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Eliminar una notificación',
        responses={204: openapi.Response('Eliminada'),
                   403: 'No tiene permisos',
                   404: 'No encontrada'},
        tags=['Notificaciones'],
    )
    def destroy(self, request, *args, **kwargs):
        """Elimina una notificación propia."""
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        method='patch',
        operation_summary='Marcar una notificación como leída',
        responses={200: NotificacionListSerializer,
                   404: 'No encontrada'},
        tags=['Notificaciones'],
    )
    @action(detail=True, methods=['patch'], url_path='marcar-leida')
    def marcar_leida(self, request, pk=None):
        """Marca ``leida=True`` y sella ``read_at`` (idempotente)."""
        notif = self.get_object()
        if not notif.leida:
            notif.leida = True
            notif.read_at = timezone.now()
            notif.save(update_fields=['leida', 'read_at'])
        return Response(NotificacionListSerializer(notif).data)

    @swagger_auto_schema(
        method='post',
        operation_summary='Marcar todas mis notificaciones como leídas',
        operation_description=(
            'Pone en ``leida=True`` todas las notificaciones no leídas del '
            'usuario autenticado y devuelve el conteo de filas actualizadas.'
        ),
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT),
        responses={
            200: openapi.Response(
                'Conteo',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={'actualizadas': openapi.Schema(
                        type=openapi.TYPE_INTEGER)},
                ),
            ),
        },
        tags=['Notificaciones'],
    )
    @action(detail=False, methods=['post'], url_path='marcar-todas-leidas')
    def marcar_todas_leidas(self, request):
        """Bulk: marca todas las no leídas del usuario autenticado."""
        ahora = timezone.now()
        actualizadas = Notificacion.objects.filter(
            usuario=request.user, leida=False,
        ).update(leida=True, read_at=ahora)
        return Response({'actualizadas': actualizadas}, status=status.HTTP_200_OK)
