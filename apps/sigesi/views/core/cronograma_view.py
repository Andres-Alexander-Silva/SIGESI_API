import django_filters
from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import Cronograma, User
from apps.sigesi.serializers.core.cronograma_serializer import (
    CronogramaListSerializer,
    CronogramaCreateUpdateSerializer,
)
from apps.sigesi.decorators.permissions import CronogramaRolePermission


class CronogramaFilter(django_filters.FilterSet):
    """Filtra cronogramas por semillero y semestre del plan de acción."""

    semillero = django_filters.NumberFilter(field_name='plan_accion__semillero')
    semestre = django_filters.CharFilter(field_name='plan_accion__semestre')

    class Meta:
        model = Cronograma
        fields = ['plan_accion', 'semillero', 'semestre']


class CronogramaViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para los cronogramas, con control de acceso por rol.

    El listado admite los filtros opcionales ``?semillero=`` y ``?semestre=``
    (resueltos a través del plan de acción), además de ``?plan_accion=``.
    """

    queryset = (
        Cronograma.objects.all()
        .select_related('plan_accion__semillero', 'responsable')
        .prefetch_related('actividades')
    )
    permission_classes = [CronogramaRolePermission]
    filterset_class = CronogramaFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CronogramaCreateUpdateSerializer
        return CronogramaListSerializer

    def get_queryset(self):
        """Filtra los cronogramas según el rol del usuario autenticado."""
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_authenticated:
            return queryset.none()

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return queryset

        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return queryset.filter(
                plan_accion__semillero__grupo_investigacion__director=user
            ).distinct()

        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return queryset.filter(plan_accion__semillero__director=user).distinct()

        if user.tiene_rol(User.RolChoices.LIDER_ESTUDIANTIL):
            return queryset.filter(
                plan_accion__semillero__lider_estudiantil=user
            ).distinct()

        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return queryset.filter(
                plan_accion__semillero__matriculas__estudiante=user
            ).distinct()

        return queryset.none()

    @swagger_auto_schema(
        operation_summary='Listar cronogramas',
        operation_description=(
            'Retorna los cronogramas visibles para el usuario autenticado. '
            'Admite los filtros opcionales `semillero`, `semestre` y `plan_accion`.'
        ),
        manual_parameters=[
            openapi.Parameter(
                'semillero', openapi.IN_QUERY,
                description='Filtrar por ID de semillero (vía plan de acción).',
                type=openapi.TYPE_INTEGER, required=False,
            ),
            openapi.Parameter(
                'semestre', openapi.IN_QUERY,
                description='Filtrar por semestre (ej: 2025-1, vía plan de acción).',
                type=openapi.TYPE_STRING, required=False,
            ),
        ],
        responses={200: CronogramaListSerializer(many=True)},
        tags=['Cronograma'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Consultar detalle de cronograma',
        responses={200: CronogramaListSerializer, 404: 'Cronograma no encontrado'},
        tags=['Cronograma'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Crear cronograma',
        request_body=CronogramaCreateUpdateSerializer,
        responses={
            201: CronogramaListSerializer,
            400: openapi.Response('Errores de validación'),
            403: openapi.Response('No tiene permisos'),
        },
        tags=['Cronograma'],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cronograma = serializer.save()
        return Response(
            {
                'message': 'Cronograma creado con éxito',
                'data': CronogramaListSerializer(cronograma).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Actualizar cronograma',
        request_body=CronogramaCreateUpdateSerializer,
        responses={
            200: CronogramaListSerializer,
            400: 'Errores de validación',
            403: 'No tiene permisos',
            404: 'Cronograma no encontrado',
        },
        tags=['Cronograma'],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Actualizar cronograma (parcial)',
        request_body=CronogramaCreateUpdateSerializer,
        responses={
            200: CronogramaListSerializer,
            400: 'Errores de validación',
            403: 'No tiene permisos',
            404: 'Cronograma no encontrado',
        },
        tags=['Cronograma'],
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
        tags=['Cronograma'],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
