from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from apps.sigesi.models import PlanEstrategico, User
from apps.sigesi.serializers.core.plan_estrategico_serializer import (
    PlanEstrategicoListSerializer,
    PlanEstrategicoCreateUpdateSerializer,
)
from apps.sigesi.decorators.permissions import PlanEstrategicoRolePermission


class PlanEstrategicoViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para los planes estratégicos anuales del semillero.

    Cada semillero tiene a lo sumo un plan estratégico por año. El listado
    admite los filtros opcionales ``?semillero=``, ``?anio=`` y ``?estado=``.
    El control de acceso por rol lo aplican ``PlanEstrategicoRolePermission``
    (a nivel de método/objeto) y ``get_queryset`` (alcance por filas).
    """

    queryset = (
        PlanEstrategico.objects.all()
        .select_related(
            'semillero',
            'semillero__grupo_investigacion',
            'semillero__director',
        )
    )
    permission_classes = [PlanEstrategicoRolePermission]
    filterset_fields = ['semillero', 'anio', 'estado']

    def get_serializer_class(self):
        """Usa el serializador de escritura en create/update y el de lectura en el resto."""
        if self.action in ['create', 'update', 'partial_update']:
            return PlanEstrategicoCreateUpdateSerializer
        return PlanEstrategicoListSerializer

    def get_queryset(self):
        """Filtra los planes estratégicos según el rol del usuario autenticado."""
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
        operation_summary='Listar planes estratégicos',
        operation_description=(
            'Retorna los planes estratégicos visibles para el usuario '
            'autenticado. Admite los filtros opcionales `semillero`, `anio` y '
            '`estado`.'
        ),
        manual_parameters=[
            openapi.Parameter(
                'semillero', openapi.IN_QUERY,
                description='Filtrar por ID de semillero.',
                type=openapi.TYPE_INTEGER, required=False,
            ),
            openapi.Parameter(
                'anio', openapi.IN_QUERY,
                description='Filtrar por año (ej: 2025).',
                type=openapi.TYPE_INTEGER, required=False,
            ),
            openapi.Parameter(
                'estado', openapi.IN_QUERY,
                description='Filtrar por estado del plan.',
                type=openapi.TYPE_STRING, required=False,
            ),
        ],
        responses={200: PlanEstrategicoListSerializer(many=True)},
        tags=['Plan Estratégico'],
    )
    def list(self, request, *args, **kwargs):
        """Lista los planes estratégicos visibles para el usuario."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Consultar detalle de plan estratégico',
        responses={200: PlanEstrategicoListSerializer, 404: 'Plan estratégico no encontrado'},
        tags=['Plan Estratégico'],
    )
    def retrieve(self, request, *args, **kwargs):
        """Devuelve el detalle de un plan estratégico, incluyendo el semillero."""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Crear plan estratégico',
        request_body=PlanEstrategicoCreateUpdateSerializer,
        responses={
            201: PlanEstrategicoListSerializer,
            400: openapi.Response('Errores de validación (incluye duplicado semillero/año)'),
            403: openapi.Response('No tiene permisos'),
        },
        tags=['Plan Estratégico'],
    )
    def create(self, request, *args, **kwargs):
        """Crea un plan estratégico y responde con su representación de lectura."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()
        return Response(
            {
                'message': 'Plan estratégico creado con éxito',
                'data': PlanEstrategicoListSerializer(plan).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Actualizar plan estratégico',
        request_body=PlanEstrategicoCreateUpdateSerializer,
        responses={
            200: PlanEstrategicoListSerializer,
            400: 'Errores de validación',
            403: 'No tiene permisos (p. ej. cambiar estado sin ser Admin/Director de Grupo)',
            404: 'Plan estratégico no encontrado',
        },
        tags=['Plan Estratégico'],
    )
    def update(self, request, *args, **kwargs):
        """Actualiza por completo un plan estratégico."""
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Actualizar plan estratégico (parcial)',
        request_body=PlanEstrategicoCreateUpdateSerializer,
        responses={
            200: PlanEstrategicoListSerializer,
            400: 'Errores de validación',
            403: 'No tiene permisos (p. ej. cambiar estado sin ser Admin/Director de Grupo)',
            404: 'Plan estratégico no encontrado',
        },
        tags=['Plan Estratégico'],
    )
    def partial_update(self, request, *args, **kwargs):
        """Actualiza parcialmente un plan estratégico."""
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Eliminar plan estratégico',
        responses={
            204: openapi.Response('Plan estratégico eliminado correctamente'),
            403: openapi.Response('No tiene permisos'),
            404: openapi.Response('Plan estratégico no encontrado'),
        },
        tags=['Plan Estratégico'],
    )
    def destroy(self, request, *args, **kwargs):
        """Elimina un plan estratégico."""
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Aprobar plan estratégico',
        operation_description=(
            'Aprueba el plan estratégico indicado. Solo el Administrador y el '
            'Director de Grupo (del grupo al que pertenece el semillero) pueden '
            'aprobar. No requiere cuerpo: marca `estado=aprobado`, fija '
            '`aprobado_por` al usuario autenticado y `fecha_aprobacion` a la '
            'fecha de la solicitud.'
        ),
        request_body=no_body,
        responses={
            200: PlanEstrategicoListSerializer,
            400: openapi.Response('El plan estratégico ya está aprobado'),
            403: openapi.Response('No tiene permisos para aprobar'),
            404: openapi.Response('Plan estratégico no encontrado'),
        },
        tags=['Plan Estratégico'],
    )
    @action(detail=True, methods=['post'], url_path='aprobar')
    def aprobar(self, request, pk=None):
        """Aprueba un plan estratégico (solo Administrador / Director de Grupo).

        Restringe el acceso a Administrador y Director de Grupo; ``get_object()``
        aplica el filtro de queryset y ``has_object_permission``, de modo que el
        Director de Grupo solo puede aprobar planes de los semilleros de su
        grupo. Si el plan ya está aprobado responde 400.
        """
        user = request.user

        # Solo Administrador y Director de Grupo pueden aprobar.
        if not user.tiene_alguno_de([
            User.RolChoices.ADMINISTRADOR,
            User.RolChoices.DIRECTOR_GRUPO,
        ]):
            return Response(
                {'error': 'Solo el Administrador o el Director de Grupo pueden aprobar un plan estratégico.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # get_object() aplica el filtro de queryset y has_object_permission,
        # de modo que el Director de Grupo solo alcanza planes de su grupo.
        plan = self.get_object()

        if plan.estado == PlanEstrategico.EstadoChoices.APROBADO:
            return Response(
                {'error': 'El plan estratégico ya está aprobado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan.estado = PlanEstrategico.EstadoChoices.APROBADO
        plan.aprobado_por = user
        plan.fecha_aprobacion = timezone.now()
        plan.save(update_fields=['estado', 'aprobado_por', 'fecha_aprobacion', 'updated_at'])

        return Response(
            {
                'message': 'Plan estratégico aprobado con éxito',
                'data': PlanEstrategicoListSerializer(plan).data,
            },
            status=status.HTTP_200_OK,
        )
