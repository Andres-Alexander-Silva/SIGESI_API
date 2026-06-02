from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import ActividadCronograma, User
from apps.sigesi.serializers.core.actividad_cronograma_serializer import (
    ActividadCronogramaListSerializer,
    ActividadCronogramaCreateUpdateSerializer,
)
from apps.sigesi.decorators.permissions import ActividadCronogramaRolePermission


class ActividadCronogramaViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para las actividades de un cronograma, con acceso por rol."""

    queryset = (
        ActividadCronograma.objects.all()
        .select_related('cronograma__plan_accion__semillero', 'responsable')
    )
    permission_classes = [ActividadCronogramaRolePermission]
    filterset_fields = ['cronograma', 'responsable']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ActividadCronogramaCreateUpdateSerializer
        return ActividadCronogramaListSerializer

    def get_queryset(self):
        """Filtra las actividades según el rol del usuario autenticado."""
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_authenticated:
            return queryset.none()

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return queryset

        base = 'cronograma__plan_accion__semillero'

        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return queryset.filter(
                **{f'{base}__grupo_investigacion__director': user}
            ).distinct()

        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return queryset.filter(**{f'{base}__director': user}).distinct()

        if user.tiene_rol(User.RolChoices.LIDER_ESTUDIANTIL):
            return queryset.filter(**{f'{base}__lider_estudiantil': user}).distinct()

        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return queryset.filter(**{f'{base}__matriculas__estudiante': user}).distinct()

        return queryset.none()

    @swagger_auto_schema(
        operation_summary='Listar actividades de cronograma',
        responses={200: ActividadCronogramaListSerializer(many=True)},
        tags=['Actividad de Cronograma'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Consultar detalle de actividad de cronograma',
        responses={200: ActividadCronogramaListSerializer, 404: 'No encontrada'},
        tags=['Actividad de Cronograma'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Crear actividad de cronograma',
        request_body=ActividadCronogramaCreateUpdateSerializer,
        responses={
            201: ActividadCronogramaListSerializer,
            400: openapi.Response('Errores de validación'),
            403: openapi.Response('No tiene permisos'),
        },
        tags=['Actividad de Cronograma'],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actividad = serializer.save()
        return Response(
            {
                'message': 'Actividad de cronograma creada con éxito',
                'data': ActividadCronogramaListSerializer(actividad).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Actualizar actividad de cronograma',
        request_body=ActividadCronogramaCreateUpdateSerializer,
        responses={
            200: ActividadCronogramaListSerializer,
            400: 'Errores de validación',
            403: 'No tiene permisos',
            404: 'No encontrada',
        },
        tags=['Actividad de Cronograma'],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Actualizar actividad de cronograma (parcial)',
        request_body=ActividadCronogramaCreateUpdateSerializer,
        responses={
            200: ActividadCronogramaListSerializer,
            400: 'Errores de validación',
            403: 'No tiene permisos',
            404: 'No encontrada',
        },
        tags=['Actividad de Cronograma'],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Eliminar actividad de cronograma',
        responses={
            204: openapi.Response('Actividad eliminada correctamente'),
            403: openapi.Response('No tiene permisos'),
            404: openapi.Response('No encontrada'),
        },
        tags=['Actividad de Cronograma'],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
