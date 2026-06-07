from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils.decorators import method_decorator

from apps.sigesi.models import Evento
from apps.sigesi.serializers.core.evento_serializer import (
    EventoListSerializer,
    EventoCreateUpdateSerializer,
)
from apps.sigesi.decorators.permissions import AdminOrReadOnlyPermission


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_summary='Listar eventos',
    manual_parameters=[
        openapi.Parameter('estado', openapi.IN_QUERY, description='Filtrar por estado.',
                          type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('modalidad', openapi.IN_QUERY, description='Filtrar por modalidad.',
                          type=openapi.TYPE_STRING, required=False),
    ],
    responses={200: EventoListSerializer(many=True)},
    tags=['Eventos'],
))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(
    operation_summary='Consultar detalle de evento',
    responses={200: EventoListSerializer, 404: 'Evento no encontrado'},
    tags=['Eventos'],
))
@method_decorator(name='update', decorator=swagger_auto_schema(
    operation_summary='Actualizar evento',
    request_body=EventoCreateUpdateSerializer,
    responses={200: EventoListSerializer, 400: 'Errores de validación',
               403: 'No tiene permisos', 404: 'Evento no encontrado'},
    tags=['Eventos'],
))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(
    operation_summary='Actualizar evento (parcial)',
    request_body=EventoCreateUpdateSerializer,
    responses={200: EventoListSerializer, 400: 'Errores de validación',
               403: 'No tiene permisos', 404: 'Evento no encontrado'},
    tags=['Eventos'],
))
@method_decorator(name='destroy', decorator=swagger_auto_schema(
    operation_summary='Eliminar evento',
    responses={204: openapi.Response('Evento eliminado correctamente'),
               403: openapi.Response('No tiene permisos'),
               404: openapi.Response('Evento no encontrado')},
    tags=['Eventos'],
))
class EventoViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para los eventos académicos.

    Solo el Administrador puede crear, actualizar o eliminar eventos
    (``AdminOrReadOnlyPermission``); el resto de roles autenticados tiene acceso
    de solo lectura. Admite filtrar por ``estado`` y ``modalidad``.
    """

    queryset = Evento.objects.all()
    permission_classes = [AdminOrReadOnlyPermission]
    filterset_fields = ['estado', 'modalidad']

    def get_serializer_class(self):
        """Usa el serializador de escritura en create/update y el de lectura en el resto."""
        if self.action in ['create', 'update', 'partial_update']:
            return EventoCreateUpdateSerializer
        return EventoListSerializer

    @swagger_auto_schema(
        operation_summary='Crear evento',
        request_body=EventoCreateUpdateSerializer,
        responses={
            201: EventoListSerializer,
            400: openapi.Response('Errores de validación'),
            403: openapi.Response('No tiene permisos'),
        },
        tags=['Eventos'],
    )
    def create(self, request, *args, **kwargs):
        """Crea un evento (solo administrador) y responde con su representación de lectura."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evento = serializer.save()
        return Response(
            {
                'message': 'Evento creado con éxito',
                'data': EventoListSerializer(evento).data,
            },
            status=status.HTTP_201_CREATED,
        )
