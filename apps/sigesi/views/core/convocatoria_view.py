from django.utils.decorators import method_decorator
from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import Convocatoria
from apps.sigesi.serializers.core.convocatoria_serializer import (
    ConvocatoriaListSerializer,
    ConvocatoriaCreateUpdateSerializer,
)
from apps.sigesi.decorators.permissions import ConvocatoriaRolePermission
from apps.sigesi.utils.notifications import (
    notificar_evento_a_usuarios,
    _resolve_recipients_convocatoria,
)


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_summary='Listar convocatorias',
    manual_parameters=[
        openapi.Parameter('evento', openapi.IN_QUERY, description='Filtrar por ID de evento.',
                          type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('estado', openapi.IN_QUERY, description='Filtrar por estado.',
                          type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('tipo', openapi.IN_QUERY, description='Filtrar por tipo (interna/externa).',
                          type=openapi.TYPE_STRING, required=False),
    ],
    responses={200: ConvocatoriaListSerializer(many=True)},
    tags=['Convocatorias'],
))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(
    operation_summary='Consultar detalle de convocatoria',
    responses={200: ConvocatoriaListSerializer, 404: 'Convocatoria no encontrada'},
    tags=['Convocatorias'],
))
@method_decorator(name='destroy', decorator=swagger_auto_schema(
    operation_summary='Eliminar convocatoria',
    responses={204: openapi.Response('Convocatoria eliminada correctamente'),
               403: openapi.Response('No tiene permisos'),
               404: openapi.Response('Convocatoria no encontrada')},
    tags=['Convocatorias'],
))
class ConvocatoriaViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para las convocatorias asociadas a un evento.

    El Administrador y el Director de Grupo crean, actualizan o eliminan
    convocatorias (``ConvocatoriaRolePermission``); el resto de roles
    autenticados tiene acceso de solo lectura. Admite filtrar por ``evento``,
    ``estado`` y ``tipo``.
    """

    queryset = Convocatoria.objects.all().select_related('evento')
    permission_classes = [ConvocatoriaRolePermission]
    filterset_fields = ['evento', 'estado', 'tipo']

    def get_serializer_class(self):
        """Usa el serializador de escritura en create/update y el de lectura en el resto."""
        if self.action in ['create', 'update', 'partial_update']:
            return ConvocatoriaCreateUpdateSerializer
        return ConvocatoriaListSerializer

    @swagger_auto_schema(
        operation_summary='Crear convocatoria',
        request_body=ConvocatoriaCreateUpdateSerializer,
        responses={
            201: ConvocatoriaListSerializer,
            400: openapi.Response('Errores de validación'),
            403: openapi.Response('No tiene permisos'),
        },
        tags=['Convocatorias'],
    )
    def create(self, request, *args, **kwargs):
        """Crea una convocatoria (Administrador / Director de Grupo) y notifica a director_semilleros."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        convocatoria = serializer.save()
        # Notificación: notificar a todos los director_semillero (excepto al actor).
        notificar_evento_a_usuarios(
            _resolve_recipients_convocatoria(excluir=request.user),
            tipo='convocatoria_creada',
            titulo=f'Nueva convocatoria: {convocatoria.titulo}',
            mensaje=(
                f'Se abrió la convocatoria "{convocatoria.titulo}" para el '
                f'evento "{convocatoria.evento.nombre}". '
                f'Cierre: {convocatoria.fecha_cierre}.'
            ),
            target=convocatoria,
        )
        return Response(
            {
                'message': 'Convocatoria creada con éxito',
                'data': ConvocatoriaListSerializer(convocatoria).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Actualizar convocatoria',
        request_body=ConvocatoriaCreateUpdateSerializer,
        responses={200: ConvocatoriaListSerializer, 400: 'Errores de validación',
                   403: 'No tiene permisos', 404: 'Convocatoria no encontrada'},
        tags=['Convocatorias'],
    )
    def update(self, request, *args, **kwargs):
        """Actualiza por completo una convocatoria; notifica solo si cambia ``estado``."""
        convocatoria = self.get_object()
        estado_anterior = convocatoria.estado
        response = super().update(request, *args, **kwargs)
        convocatoria.refresh_from_db()
        if convocatoria.estado != estado_anterior:
            self._emitir_actualizacion(
                convocatoria, estado_anterior, actor=request.user)
        return response

    @swagger_auto_schema(
        operation_summary='Actualizar convocatoria (parcial)',
        request_body=ConvocatoriaCreateUpdateSerializer,
        responses={200: ConvocatoriaListSerializer, 400: 'Errores de validación',
                   403: 'No tiene permisos', 404: 'Convocatoria no encontrada'},
        tags=['Convocatorias'],
    )
    def partial_update(self, request, *args, **kwargs):
        """Actualiza parcialmente; notifica solo si cambia ``estado``."""
        convocatoria = self.get_object()
        estado_anterior = convocatoria.estado
        response = super().partial_update(request, *args, **kwargs)
        convocatoria.refresh_from_db()
        if convocatoria.estado != estado_anterior:
            self._emitir_actualizacion(
                convocatoria, estado_anterior, actor=request.user)
        return response

    @staticmethod
    def _emitir_actualizacion(convocatoria, estado_anterior, *, actor):
        """Notifica a director_semilleros de un cambio de estado en la convocatoria."""
        notificar_evento_a_usuarios(
            _resolve_recipients_convocatoria(excluir=actor),
            tipo='convocatoria_actualizada',
            titulo=f'Convocatoria actualizada: {convocatoria.titulo}',
            mensaje=(
                f'La convocatoria "{convocatoria.titulo}" cambió de estado '
                f'"{estado_anterior}" a "{convocatoria.estado}".'
            ),
            target=convocatoria,
        )
