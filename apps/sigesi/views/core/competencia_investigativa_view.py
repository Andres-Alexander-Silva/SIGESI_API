from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import CompetenciaInvestigativa, User
from apps.sigesi.serializers.core.competencia_investigativa_serializer import (
    CompetenciaInvestigativaListSerializer,
    CompetenciaInvestigativaCreateUpdateSerializer,
)
from apps.sigesi.decorators.permissions import CompetenciaInvestigativaRolePermission


class CompetenciaInvestigativaViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para las competencias investigativas de cada semillero.

    El listado admite los filtros opcionales ``?semillero=``, ``?nivel=`` y
    ``?is_active=``. El control de acceso por rol lo aplican
    ``CompetenciaInvestigativaRolePermission`` (a nivel de método/objeto) y
    ``get_queryset`` (alcance por filas): el Administrador tiene CRUD completo,
    el Director de Grupo solo lee las de los semilleros de su grupo, el Director
    de Semillero lee y actualiza las de su propio semillero, y el Líder
    Estudiantil / Estudiante solo leen las de su semillero.
    """

    queryset = (
        CompetenciaInvestigativa.objects.all()
        .select_related(
            'semillero',
            'semillero__grupo_investigacion',
            'semillero__director',
        )
    )
    permission_classes = [CompetenciaInvestigativaRolePermission]
    filterset_fields = ['semillero', 'nivel', 'is_active']

    def get_serializer_class(self):
        """Usa el serializador de escritura en create/update y el de lectura en el resto."""
        if self.action in ['create', 'update', 'partial_update']:
            return CompetenciaInvestigativaCreateUpdateSerializer
        return CompetenciaInvestigativaListSerializer

    def get_queryset(self):
        """Filtra las competencias investigativas según el rol del usuario autenticado."""
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
        operation_summary='Listar competencias investigativas',
        operation_description=(
            'Retorna las competencias investigativas visibles para el usuario '
            'autenticado. Admite los filtros opcionales `semillero`, `nivel` e '
            '`is_active`.'
        ),
        manual_parameters=[
            openapi.Parameter(
                'semillero', openapi.IN_QUERY,
                description='Filtrar por ID de semillero.',
                type=openapi.TYPE_INTEGER, required=False,
            ),
            openapi.Parameter(
                'nivel', openapi.IN_QUERY,
                description='Filtrar por nivel (basico, intermedio, avanzado).',
                type=openapi.TYPE_STRING, required=False,
            ),
            openapi.Parameter(
                'is_active', openapi.IN_QUERY,
                description='Filtrar por estado activo (true/false).',
                type=openapi.TYPE_BOOLEAN, required=False,
            ),
        ],
        responses={200: CompetenciaInvestigativaListSerializer(many=True)},
        tags=['Competencias Investigativas'],
    )
    def list(self, request, *args, **kwargs):
        """Lista las competencias investigativas visibles para el usuario."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Consultar detalle de competencia investigativa',
        responses={200: CompetenciaInvestigativaListSerializer, 404: 'Competencia no encontrada'},
        tags=['Competencias Investigativas'],
    )
    def retrieve(self, request, *args, **kwargs):
        """Devuelve el detalle de una competencia, incluyendo el semillero."""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Crear competencia investigativa',
        request_body=CompetenciaInvestigativaCreateUpdateSerializer,
        responses={
            201: CompetenciaInvestigativaListSerializer,
            400: openapi.Response('Errores de validación (incluye aval no aprobado)'),
            403: openapi.Response('No tiene permisos'),
        },
        tags=['Competencias Investigativas'],
    )
    def create(self, request, *args, **kwargs):
        """Crea una competencia investigativa y responde con su representación de lectura."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        competencia = serializer.save()
        return Response(
            {
                'message': 'Competencia investigativa creada con éxito',
                'data': CompetenciaInvestigativaListSerializer(competencia).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Actualizar competencia investigativa',
        request_body=CompetenciaInvestigativaCreateUpdateSerializer,
        responses={
            200: CompetenciaInvestigativaListSerializer,
            400: 'Errores de validación (incluye aval no aprobado)',
            403: 'No tiene permisos',
            404: 'Competencia no encontrada',
        },
        tags=['Competencias Investigativas'],
    )
    def update(self, request, *args, **kwargs):
        """Actualiza por completo una competencia investigativa."""
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Actualizar competencia investigativa (parcial)',
        request_body=CompetenciaInvestigativaCreateUpdateSerializer,
        responses={
            200: CompetenciaInvestigativaListSerializer,
            400: 'Errores de validación (incluye aval no aprobado)',
            403: 'No tiene permisos',
            404: 'Competencia no encontrada',
        },
        tags=['Competencias Investigativas'],
    )
    def partial_update(self, request, *args, **kwargs):
        """Actualiza parcialmente una competencia investigativa."""
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Eliminar competencia investigativa',
        responses={
            204: openapi.Response('Competencia eliminada correctamente'),
            403: openapi.Response('No tiene permisos'),
            404: openapi.Response('Competencia no encontrada'),
        },
        tags=['Competencias Investigativas'],
    )
    def destroy(self, request, *args, **kwargs):
        """Elimina una competencia investigativa."""
        return super().destroy(request, *args, **kwargs)
