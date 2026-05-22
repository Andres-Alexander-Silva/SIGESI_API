from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from apps.sigesi.models import PlanAccion, User
from apps.sigesi.serializers.core.plan_accion_serializer import (
    PlanAccionListSerializer,
    PlanAccionCreateUpdateSerializer,
)
from apps.sigesi.decorators.permissions import PlanAccionRolePermission


class PlanAccionViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para los planes de acción, con control de acceso por rol.

    El listado admite los filtros opcionales ``?semillero=`` y ``?semestre=``.
    """

    queryset = (
        PlanAccion.objects.all()
        .select_related('semillero', 'plan_estrategico', 'aprobado_por')
    )
    permission_classes = [PlanAccionRolePermission]
    filterset_fields = ['semillero', 'semestre']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PlanAccionCreateUpdateSerializer
        return PlanAccionListSerializer

    def get_queryset(self):
        """Filtra los planes de acción según el rol del usuario autenticado."""
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_authenticated:
            return queryset.none()

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return queryset

        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return queryset.filter(
                semillero__grupo_investigacion__director=user
            ).distinct()

        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return queryset.filter(semillero__director=user).distinct()

        if user.tiene_rol(User.RolChoices.LIDER_ESTUDIANTIL):
            return queryset.filter(semillero__lider_estudiantil=user).distinct()

        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return queryset.filter(semillero__matriculas__estudiante=user).distinct()

        return queryset.none()

    @swagger_auto_schema(
        operation_summary='Listar planes de acción',
        operation_description=(
            'Retorna los planes de acción visibles para el usuario autenticado. '
            'Admite los filtros opcionales `semillero` y `semestre`.'
        ),
        manual_parameters=[
            openapi.Parameter(
                'semillero', openapi.IN_QUERY,
                description='Filtrar por ID de semillero.',
                type=openapi.TYPE_INTEGER, required=False,
            ),
            openapi.Parameter(
                'semestre', openapi.IN_QUERY,
                description='Filtrar por semestre (ej: 2025-1).',
                type=openapi.TYPE_STRING, required=False,
            ),
        ],
        responses={200: PlanAccionListSerializer(many=True)},
        tags=['Plan de Acción'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Consultar detalle de plan de acción',
        responses={200: PlanAccionListSerializer, 404: 'Plan de acción no encontrado'},
        tags=['Plan de Acción'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Crear plan de acción',
        request_body=PlanAccionCreateUpdateSerializer,
        responses={
            201: PlanAccionListSerializer,
            400: openapi.Response('Errores de validación'),
            403: openapi.Response('No tiene permisos'),
        },
        tags=['Plan de Acción'],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()
        return Response(
            {
                'message': 'Plan de acción creado con éxito',
                'data': PlanAccionListSerializer(plan).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Actualizar plan de acción',
        request_body=PlanAccionCreateUpdateSerializer,
        responses={
            200: PlanAccionListSerializer,
            400: 'Errores de validación',
            403: 'No tiene permisos',
            404: 'Plan de acción no encontrado',
        },
        tags=['Plan de Acción'],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Actualizar plan de acción (parcial)',
        request_body=PlanAccionCreateUpdateSerializer,
        responses={
            200: PlanAccionListSerializer,
            400: 'Errores de validación',
            403: 'No tiene permisos',
            404: 'Plan de acción no encontrado',
        },
        tags=['Plan de Acción'],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Eliminar plan de acción',
        responses={
            204: openapi.Response('Plan de acción eliminado correctamente'),
            403: openapi.Response('No tiene permisos'),
            404: openapi.Response('Plan de acción no encontrado'),
        },
        tags=['Plan de Acción'],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Aprobar plan de acción',
        operation_description=(
            'Aprueba el plan de acción indicado. Solo el Administrador y el '
            'Director de Grupo (del grupo al que pertenece el semillero) pueden '
            'aprobar. No requiere cuerpo: marca `estado=aprobado`, fija '
            '`aprobado_por` al usuario autenticado y `fecha_aprobacion` a la '
            'fecha de la solicitud.'
        ),
        request_body=no_body,
        responses={
            200: PlanAccionListSerializer,
            403: openapi.Response('No tiene permisos para aprobar'),
            404: openapi.Response('Plan de acción no encontrado'),
        },
        tags=['Plan de Acción'],
    )
    @action(detail=True, methods=['post'], url_path='aprobar')
    def aprobar(self, request, pk=None):
        user = request.user

        # Solo Administrador y Director de Grupo pueden aprobar.
        if not user.tiene_alguno_de([
            User.RolChoices.ADMINISTRADOR,
            User.RolChoices.DIRECTOR_GRUPO,
        ]):
            return Response(
                {'error': 'Solo el Administrador o el Director de Grupo pueden aprobar un plan de acción.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # get_object() aplica el filtro de queryset y has_object_permission,
        # de modo que el Director de Grupo solo alcanza planes de su grupo.
        plan = self.get_object()

        plan.estado = PlanAccion.EstadoChoices.APROBADO
        plan.aprobado_por = user
        plan.fecha_aprobacion = timezone.now()
        plan.save(update_fields=['estado', 'aprobado_por', 'fecha_aprobacion', 'updated_at'])

        return Response(
            {
                'message': 'Plan de acción aprobado con éxito',
                'data': PlanAccionListSerializer(plan).data,
            },
            status=status.HTTP_200_OK,
        )
