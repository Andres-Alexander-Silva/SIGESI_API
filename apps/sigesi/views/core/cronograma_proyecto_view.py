from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import CronogramaProyecto, User
from apps.sigesi.serializers.core.cronograma_proyecto_serializer import (
    CronogramaProyectoListSerializer,
    CronogramaProyectoCreateUpdateSerializer,
)
from apps.sigesi.decorators.permissions import CronogramaProyectoRolePermission


class CronogramaProyectoViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para los cronogramas de proyecto, con control de acceso por rol."""

    queryset = (
        CronogramaProyecto.objects.all()
        .select_related('proyecto')
        .order_by('proyecto', 'fecha_inicio')
    )
    permission_classes = [CronogramaProyectoRolePermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ['proyecto', 'estado_actividad']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CronogramaProyectoCreateUpdateSerializer
        return CronogramaProyectoListSerializer

    def get_queryset(self):
        """Filtra los cronogramas según el rol del usuario autenticado."""
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_authenticated:
            return queryset.none()

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return queryset

        if user.tiene_alguno_de([User.RolChoices.DIRECTOR_SEMILLERO, User.RolChoices.DIRECTOR_GRUPO]):
            return queryset.filter(
                models.Q(proyecto__director=user) |
                models.Q(proyecto__semilleros__director=user) |
                models.Q(proyecto__semilleros__grupo_investigacion__director=user)
            ).distinct()

        if user.tiene_alguno_de([User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL]):
            return queryset.filter(
                models.Q(proyecto__lider=user) |
                models.Q(proyecto__estudiantes=user)
            ).distinct()

        return queryset.none()

    @swagger_auto_schema(
        operation_summary='Listar cronogramas de proyecto',
        operation_description='Retorna la lista de cronogramas permitidos para el usuario autenticado.',
        responses={200: CronogramaProyectoListSerializer(many=True)},
        tags=['Cronograma Proyecto'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Consultar detalle de cronograma',
        responses={200: CronogramaProyectoListSerializer, 404: 'Cronograma no encontrado'},
        tags=['Cronograma Proyecto'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Crear entrada de cronograma',
        request_body=CronogramaProyectoCreateUpdateSerializer,
        responses={
            201: CronogramaProyectoListSerializer,
            400: openapi.Response('Errores de validación'),
            403: openapi.Response('No tiene permisos'),
        },
        tags=['Cronograma Proyecto'],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cronograma = serializer.save()
        return Response(
            {
                'message': 'Cronograma creado con éxito',
                'data': CronogramaProyectoListSerializer(cronograma).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Actualizar cronograma',
        request_body=CronogramaProyectoCreateUpdateSerializer,
        responses={
            200: CronogramaProyectoListSerializer,
            400: 'Errores de validación',
            403: 'No tiene permisos',
            404: 'Cronograma no encontrado',
        },
        tags=['Cronograma Proyecto'],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Actualizar cronograma (parcial)',
        request_body=CronogramaProyectoCreateUpdateSerializer,
        responses={
            200: CronogramaProyectoListSerializer,
            400: 'Errores de validación',
            403: 'No tiene permisos',
            404: 'Cronograma no encontrado',
        },
        tags=['Cronograma Proyecto'],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Eliminar cronograma',
        responses={
            204: openapi.Response('Cronograma eliminado correctamente'),
            403: openapi.Response('No tiene permisos'),
            404: openapi.Response('Cronograma no encontrado'),
        },
        tags=['Cronograma Proyecto'],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Porcentaje de cumplimiento del cronograma',
        operation_description=(
            'Retorna el total de actividades, las completadas y el porcentaje de '
            'cumplimiento para el proyecto indicado, considerando el alcance de '
            'visibilidad del usuario autenticado.'
        ),
        manual_parameters=[
            openapi.Parameter(
                'proyecto',
                openapi.IN_QUERY,
                description='ID del proyecto a consultar.',
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description='Cálculo de cumplimiento',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'proyecto_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'total_actividades': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'completadas': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'porcentaje_cumplimiento': openapi.Schema(type=openapi.TYPE_NUMBER),
                    },
                ),
            ),
            400: 'Falta el query param proyecto o es inválido',
            401: 'No autenticado',
        },
        tags=['Cronograma Proyecto'],
    )
    @action(detail=False, methods=['get'], url_path='porcentaje-cumplimiento')
    def porcentaje_cumplimiento(self, request):
        proyecto_id = request.query_params.get('proyecto')
        if not proyecto_id:
            return Response(
                {'error': "Se requiere el query param 'proyecto'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            proyecto_id_int = int(proyecto_id)
        except ValueError:
            return Response(
                {'error': "El query param 'proyecto' debe ser un entero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = self.get_queryset().filter(proyecto_id=proyecto_id_int)
        total = qs.count()
        completadas = qs.filter(
            estado_actividad=CronogramaProyecto.EstadoChoices.COMPLETADA
        ).count()
        porcentaje = round(completadas / total * 100, 1) if total else 0.0

        return Response(
            {
                'proyecto_id': proyecto_id_int,
                'total_actividades': total,
                'completadas': completadas,
                'porcentaje_cumplimiento': porcentaje,
            },
            status=status.HTTP_200_OK,
        )
