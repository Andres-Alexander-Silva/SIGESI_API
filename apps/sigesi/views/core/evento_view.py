from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import Evento
from apps.sigesi.serializers.core.evento_serializer import (
    EventoListSerializer,
    EventoCreateUpdateSerializer,
)
from apps.sigesi.decorators.permissions import AdminOrReadOnlyPermission


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
        operation_summary='Listar eventos',
        manual_parameters=[
            openapi.Parameter('estado', openapi.IN_QUERY, description='Filtrar por estado.',
                              type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('modalidad', openapi.IN_QUERY, description='Filtrar por modalidad.',
                              type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: EventoListSerializer(many=True)},
        tags=['Eventos'],
    )
    def list(self, request, *args, **kwargs):
        """Lista los eventos académicos."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Consultar detalle de evento',
        responses={200: EventoListSerializer, 404: 'Evento no encontrado'},
        tags=['Eventos'],
    )
    def retrieve(self, request, *args, **kwargs):
        """Devuelve el detalle de un evento."""
        return super().retrieve(request, *args, **kwargs)

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

    @swagger_auto_schema(
        operation_summary='Actualizar evento',
        request_body=EventoCreateUpdateSerializer,
        responses={200: EventoListSerializer, 400: 'Errores de validación',
                   403: 'No tiene permisos', 404: 'Evento no encontrado'},
        tags=['Eventos'],
    )
    def update(self, request, *args, **kwargs):
        """Actualiza por completo un evento (solo administrador)."""
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Actualizar evento (parcial)',
        request_body=EventoCreateUpdateSerializer,
        responses={200: EventoListSerializer, 400: 'Errores de validación',
                   403: 'No tiene permisos', 404: 'Evento no encontrado'},
        tags=['Eventos'],
    )
    def partial_update(self, request, *args, **kwargs):
        """Actualiza parcialmente un evento (solo administrador)."""
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Eliminar evento',
        responses={204: openapi.Response('Evento eliminado correctamente'),
                   403: openapi.Response('No tiene permisos'),
                   404: openapi.Response('Evento no encontrado')},
        tags=['Eventos'],
    )
    def destroy(self, request, *args, **kwargs):
        """Elimina un evento (solo administrador)."""
        return super().destroy(request, *args, **kwargs)
