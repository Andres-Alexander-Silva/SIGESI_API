from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import ProduccionAcademica, User
from apps.sigesi.serializers.core.produccion_academica_serializer import (
    ProduccionAcademicaListSerializer,
    ProduccionAcademicaCreateUpdateSerializer,
)
from apps.sigesi.decorators.permissions import ProduccionAcademicaRolePermission
from apps.sigesi.utils.download import ArchiveDownloadMixin


class ProduccionAcademicaViewSet(ArchiveDownloadMixin, viewsets.ModelViewSet):
    """ViewSet CRUD para ProduccionAcademica.

    - Lectura (list/retrieve): cualquier usuario autenticado.
    - Escritura (create/update/destroy): solo Administrador o el director/líder
      del proyecto vinculado.
    """

    queryset = (
        ProduccionAcademica.objects.all()
        .select_related('proyecto', 'semillero', 'linea_investigacion')
        .prefetch_related('autores')
        .order_by('-fecha_publicacion', '-created_at')
    )
    permission_classes = [ProduccionAcademicaRolePermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    archive_fields = {'archivo': 'archivo', 'certificado': 'certificado'}

    filterset_fields = ['proyecto', 'semillero', 'tipo', 'estado']
    search_fields = ['titulo', 'doi', 'revista_evento']
    ordering_fields = ['titulo', 'fecha_publicacion', 'created_at']
    ordering = ['-fecha_publicacion', '-created_at']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ProduccionAcademicaCreateUpdateSerializer
        return ProduccionAcademicaListSerializer

    def _puede_escribir_en_proyecto(self, user, proyecto):
        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True
        if proyecto is None:
            return False
        return proyecto.director_id == user.id or proyecto.lider_id == user.id

    @swagger_auto_schema(
        operation_summary='Listar producciones académicas',
        operation_description='Lectura abierta a cualquier usuario autenticado.',
        responses={200: ProduccionAcademicaListSerializer(many=True)},
        tags=['Producción Académica'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Consultar detalle de producción académica',
        responses={200: ProduccionAcademicaListSerializer, 404: 'Producción no encontrada'},
        tags=['Producción Académica'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Crear producción académica',
        operation_description=(
            'Solo el administrador o el director/líder del proyecto vinculado '
            'pueden crear. El proyecto es obligatorio.'
        ),
        request_body=ProduccionAcademicaCreateUpdateSerializer,
        responses={
            201: ProduccionAcademicaListSerializer,
            400: openapi.Response('Errores de validación'),
            403: openapi.Response('No tiene permisos sobre el proyecto indicado'),
        },
        tags=['Producción Académica'],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proyecto = serializer.validated_data['proyecto']

        if not self._puede_escribir_en_proyecto(request.user, proyecto):
            return Response(
                {
                    'error': (
                        'Solo el administrador o el director/líder del proyecto '
                        'pueden crear producciones académicas para este proyecto.'
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        instance = serializer.save()
        return Response(
            ProduccionAcademicaListSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Actualizar producción académica',
        request_body=ProduccionAcademicaCreateUpdateSerializer,
        responses={
            200: ProduccionAcademicaListSerializer,
            400: 'Errores de validación',
            403: 'No tiene permisos sobre el proyecto vinculado',
            404: 'Producción no encontrada',
        },
        tags=['Producción Académica'],
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.pop('partial', False)
        )
        serializer.is_valid(raise_exception=True)

        nuevo_proyecto = serializer.validated_data.get('proyecto', instance.proyecto)
        if not self._puede_escribir_en_proyecto(request.user, nuevo_proyecto):
            return Response(
                {
                    'error': (
                        'Solo el administrador o el director/líder del proyecto '
                        'destino pueden mover esta producción a ese proyecto.'
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        instance = serializer.save()
        return Response(ProduccionAcademicaListSerializer(instance).data)

    @swagger_auto_schema(
        operation_summary='Actualizar producción académica (parcial)',
        request_body=ProduccionAcademicaCreateUpdateSerializer,
        responses={
            200: ProduccionAcademicaListSerializer,
            400: 'Errores de validación',
            403: 'No tiene permisos sobre el proyecto vinculado',
            404: 'Producción no encontrada',
        },
        tags=['Producción Académica'],
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Eliminar producción académica',
        responses={
            204: openapi.Response('Producción eliminada correctamente'),
            403: openapi.Response('No tiene permisos sobre el proyecto vinculado'),
            404: openapi.Response('Producción no encontrada'),
        },
        tags=['Producción Académica'],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
