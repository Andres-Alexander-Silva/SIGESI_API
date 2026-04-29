from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import LineaInvestigacion
from apps.sigesi.serializers.core.linea_investigacion_serializer import (
    LineaInvestigacionSerializer,
    LineaInvestigacionCreateSerializer,
    LineaInvestigacionUpdateSerializer
)
from apps.sigesi.filters.core.linea_investigacion_filter import LineaInvestigacionFilter
from apps.sigesi.utils.ordering import MultiFieldOrderingFilter

class LineaInvestigacionViewSet(viewsets.ModelViewSet):
    """
    ViewSet CRUD para la gestión de Líneas de Investigación.
    """
    queryset = LineaInvestigacion.objects.all()
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, MultiFieldOrderingFilter]
    filterset_class = LineaInvestigacionFilter

    ordering_aliases = {
        'nombre': ['nombre'],
        'fecha': ['created_at'],
    }
    ordering = ['nombre']

    def get_serializer_class(self):
        if self.action == 'create':
            return LineaInvestigacionCreateSerializer
        if self.action in ('update', 'partial_update'):
            return LineaInvestigacionUpdateSerializer
        return LineaInvestigacionSerializer

    @swagger_auto_schema(
        operation_summary="Listar líneas de investigación",
        operation_description="Retorna la lista de líneas de investigación. Soporta filtros por nombre y estado (is_active).",
        manual_parameters=[
            openapi.Parameter(
                name='ordering',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='Criterio de ordenamiento: `nombre`, `-nombre`, `fecha`, `-fecha`.',
            ),
        ],
        tags=["Core - Líneas de Investigación"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Crear línea de investigación",
        operation_description="Crea una nueva línea de investigación.",
        request_body=LineaInvestigacionCreateSerializer,
        responses={201: LineaInvestigacionSerializer},
        tags=["Core - Líneas de Investigación"]
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(LineaInvestigacionSerializer(instance).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Obtener línea de investigación",
        operation_description="Obtiene los detalles de una línea de investigación.",
        responses={200: LineaInvestigacionSerializer},
        tags=["Core - Líneas de Investigación"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Actualizar línea de investigación (completo)",
        operation_description="Actualiza una línea de investigación de forma completa.",
        request_body=LineaInvestigacionUpdateSerializer,
        responses={200: LineaInvestigacionSerializer},
        tags=["Core - Líneas de Investigación"]
    )
    def update(self, request, *args, **kwargs):
        kwargs['partial'] = False
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(LineaInvestigacionSerializer(instance).data)

    @swagger_auto_schema(
        operation_summary="Actualizar línea de investigación (parcial)",
        operation_description="Actualiza parcialmente una línea de investigación.",
        request_body=LineaInvestigacionUpdateSerializer,
        responses={200: LineaInvestigacionSerializer},
        tags=["Core - Líneas de Investigación"]
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(LineaInvestigacionSerializer(instance).data)

    @swagger_auto_schema(
        operation_summary="Eliminar línea de investigación",
        operation_description="Elimina una línea de investigación.",
        tags=["Core - Líneas de Investigación"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
