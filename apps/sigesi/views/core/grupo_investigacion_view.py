from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import GrupoInvestigacion
from apps.sigesi.serializers.core.grupo_investigacion_serializer import (
    GrupoInvestigacionSerializer,
    GrupoInvestigacionCreateSerializer,
    GrupoInvestigacionUpdateSerializer
)
from apps.sigesi.filters.core.grupo_investigacion_filter import GrupoInvestigacionFilter
from apps.sigesi.utils.ordering import MultiFieldOrderingFilter

class GrupoInvestigacionViewSet(viewsets.ModelViewSet):
    """
    ViewSet CRUD para la gestión de Grupos de Investigación.
    """
    queryset = GrupoInvestigacion.objects.all()
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, MultiFieldOrderingFilter]
    filterset_class = GrupoInvestigacionFilter

    ordering_aliases = {
        'nombre': ['nombre'],
        'fecha': ['created_at'],
    }
    ordering = ['nombre']

    def get_serializer_class(self):
        if self.action == 'create':
            return GrupoInvestigacionCreateSerializer
        if self.action in ('update', 'partial_update'):
            return GrupoInvestigacionUpdateSerializer
        return GrupoInvestigacionSerializer

    @swagger_auto_schema(
        operation_summary="Listar grupos de investigación",
        operation_description="Retorna la lista de grupos de investigación. Soporta filtros por nombre, código, programa_academico, director y estado (is_active).",
        manual_parameters=[
            openapi.Parameter(
                name='ordering',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='Criterio de ordenamiento: `nombre`, `-nombre`, `fecha`, `-fecha`.',
            ),
        ],
        tags=["Core - Grupos de Investigación"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Crear grupo de investigación",
        operation_description="Crea un nuevo grupo de investigación.",
        request_body=GrupoInvestigacionCreateSerializer,
        responses={201: GrupoInvestigacionSerializer},
        tags=["Core - Grupos de Investigación"]
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(GrupoInvestigacionSerializer(instance).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Obtener grupo de investigación",
        operation_description="Obtiene los detalles de un grupo de investigación.",
        responses={200: GrupoInvestigacionSerializer},
        tags=["Core - Grupos de Investigación"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Actualizar grupo de investigación (completo)",
        operation_description="Actualiza un grupo de investigación de forma completa.",
        request_body=GrupoInvestigacionUpdateSerializer,
        responses={200: GrupoInvestigacionSerializer},
        tags=["Core - Grupos de Investigación"]
    )
    def update(self, request, *args, **kwargs):
        kwargs['partial'] = False
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(GrupoInvestigacionSerializer(instance).data)

    @swagger_auto_schema(
        operation_summary="Actualizar grupo de investigación (parcial)",
        operation_description="Actualiza parcialmente un grupo de investigación.",
        request_body=GrupoInvestigacionUpdateSerializer,
        responses={200: GrupoInvestigacionSerializer},
        tags=["Core - Grupos de Investigación"]
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(GrupoInvestigacionSerializer(instance).data)

    @swagger_auto_schema(
        operation_summary="Eliminar grupo de investigación",
        operation_description="Elimina un grupo de investigación.",
        tags=["Core - Grupos de Investigación"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
