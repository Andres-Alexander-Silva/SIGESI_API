from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import Evaluacion, User
from apps.sigesi.serializers.core.evaluacion_serializer import (
    EvaluacionListSerializer,
    EvaluacionCreateUpdateSerializer,
    EvaluacionCalificarSerializer,
)
from apps.sigesi.decorators.permissions import (
    EvaluacionRolePermission,
    EvaluacionCalificarPermission,
)


class EvaluacionViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para las evaluaciones de competencias de los estudiantes.

    El listado admite los filtros opcionales ``?estudiante=``, ``?competencia=``,
    ``?tipo=`` y ``?semestre=``. El control de acceso por rol lo aplican
    ``EvaluacionRolePermission`` (método/objeto) y ``get_queryset`` (alcance por
    filas, anclado en ``competencia.semillero``): el Administrador tiene CRUD
    completo, el Director de Semillero CRUD sobre las evaluaciones de su propio
    semillero, y el Director de Grupo / Líder Estudiantil / Estudiante solo
    lectura de las de su ámbito.

    Al crear no se asignan ``puntaje`` ni ``observaciones``: esos campos —junto
    con ``nivel_alcanzado``— se fijan mediante la acción ``calificar``, reservada
    al evaluador de la evaluación.
    """

    queryset = (
        Evaluacion.objects.all()
        .select_related(
            'estudiante',
            'evaluador',
            'competencia',
            'competencia__semillero',
            'competencia__semillero__grupo_investigacion',
            'competencia__semillero__director',
        )
    )
    filterset_fields = ['estudiante', 'competencia', 'tipo', 'semestre']

    def get_permissions(self):
        """Usa el permiso de evaluador para ``calificar`` y el de rol para el resto."""
        if self.action == 'calificar':
            return [EvaluacionCalificarPermission()]
        return [EvaluacionRolePermission()]

    def get_serializer_class(self):
        """Serializador de escritura en create/update; de lectura en el resto."""
        if self.action in ['create', 'update', 'partial_update']:
            return EvaluacionCreateUpdateSerializer
        return EvaluacionListSerializer

    def get_queryset(self):
        """Filtra las evaluaciones según el rol del usuario autenticado."""
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_authenticated:
            return queryset.none()

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return queryset

        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return queryset.filter(
                competencia__semillero__grupo_investigacion__director=user
            ).distinct()

        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return queryset.filter(competencia__semillero__director=user).distinct()

        if user.tiene_rol(User.RolChoices.LIDER_ESTUDIANTIL):
            return queryset.filter(
                competencia__semillero__lider_estudiantil=user
            ).distinct()

        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return queryset.filter(
                competencia__semillero__matriculas__estudiante=user
            ).distinct()

        return queryset.none()

    @swagger_auto_schema(
        operation_summary='Listar evaluaciones',
        operation_description=(
            'Retorna las evaluaciones visibles para el usuario autenticado. '
            'Admite los filtros opcionales `estudiante`, `competencia`, `tipo` y '
            '`semestre`.'
        ),
        manual_parameters=[
            openapi.Parameter(
                'estudiante', openapi.IN_QUERY,
                description='Filtrar por ID del estudiante evaluado.',
                type=openapi.TYPE_INTEGER, required=False,
            ),
            openapi.Parameter(
                'competencia', openapi.IN_QUERY,
                description='Filtrar por ID de competencia.',
                type=openapi.TYPE_INTEGER, required=False,
            ),
            openapi.Parameter(
                'tipo', openapi.IN_QUERY,
                description='Filtrar por tipo (autoevaluacion, heteroevaluacion).',
                type=openapi.TYPE_STRING, required=False,
            ),
            openapi.Parameter(
                'semestre', openapi.IN_QUERY,
                description='Filtrar por semestre (ej: 2025-1).',
                type=openapi.TYPE_STRING, required=False,
            ),
        ],
        responses={200: EvaluacionListSerializer(many=True)},
        tags=['Evaluaciones'],
    )
    def list(self, request, *args, **kwargs):
        """Lista las evaluaciones visibles para el usuario."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Consultar detalle de evaluación',
        responses={200: EvaluacionListSerializer, 404: 'Evaluación no encontrada'},
        tags=['Evaluaciones'],
    )
    def retrieve(self, request, *args, **kwargs):
        """Devuelve el detalle de una evaluación, incluyendo la competencia."""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Crear evaluación',
        operation_description=(
            'Registra una evaluación. No acepta `puntaje`, `observaciones` ni '
            '`nivel_alcanzado` (se fijan luego con la acción `calificar`). Si '
            '`tipo` es `autoevaluacion` el evaluador se asigna al propio '
            'estudiante; si es `heteroevaluacion` el campo `evaluador` es '
            'obligatorio.'
        ),
        request_body=EvaluacionCreateUpdateSerializer,
        responses={
            201: EvaluacionListSerializer,
            400: openapi.Response('Errores de validación (incluye aval no aprobado)'),
            403: openapi.Response('No tiene permisos'),
        },
        tags=['Evaluaciones'],
    )
    def create(self, request, *args, **kwargs):
        """Crea una evaluación y responde con su representación de lectura."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evaluacion = serializer.save()
        return Response(
            {
                'message': 'Evaluación creada con éxito',
                'data': EvaluacionListSerializer(evaluacion).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Actualizar evaluación',
        request_body=EvaluacionCreateUpdateSerializer,
        responses={
            200: EvaluacionListSerializer,
            400: 'Errores de validación (incluye aval no aprobado)',
            403: 'No tiene permisos',
            404: 'Evaluación no encontrada',
        },
        tags=['Evaluaciones'],
    )
    def update(self, request, *args, **kwargs):
        """Actualiza por completo el encabezado de una evaluación."""
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Actualizar evaluación (parcial)',
        request_body=EvaluacionCreateUpdateSerializer,
        responses={
            200: EvaluacionListSerializer,
            400: 'Errores de validación (incluye aval no aprobado)',
            403: 'No tiene permisos',
            404: 'Evaluación no encontrada',
        },
        tags=['Evaluaciones'],
    )
    def partial_update(self, request, *args, **kwargs):
        """Actualiza parcialmente el encabezado de una evaluación."""
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Eliminar evaluación',
        responses={
            204: openapi.Response('Evaluación eliminada correctamente'),
            403: openapi.Response('No tiene permisos'),
            404: openapi.Response('Evaluación no encontrada'),
        },
        tags=['Evaluaciones'],
    )
    def destroy(self, request, *args, **kwargs):
        """Elimina una evaluación."""
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        methods=['post', 'patch'],
        operation_summary='Calificar evaluación',
        operation_description=(
            'Fija el `puntaje`, las `observaciones` y el `nivel_alcanzado` de la '
            'evaluación. Solo el evaluador asignado puede usar este endpoint. En '
            '`POST` los campos `puntaje` y `nivel_alcanzado` son obligatorios; en '
            '`PATCH` la actualización es parcial.'
        ),
        request_body=EvaluacionCalificarSerializer,
        responses={
            200: EvaluacionListSerializer,
            400: openapi.Response('Errores de validación'),
            403: openapi.Response('Solo el evaluador asignado puede calificar'),
            404: openapi.Response('Evaluación no encontrada'),
        },
        tags=['Evaluaciones'],
    )
    @action(detail=True, methods=['post', 'patch'], url_path='calificar')
    def calificar(self, request, pk=None):
        """Asigna el resultado de la evaluación (solo el evaluador asignado).

        ``get_object()`` aplica el filtro de queryset y la verificación de objeto
        de ``EvaluacionCalificarPermission``, de modo que solo el evaluador
        alcanza la evaluación. En ``POST`` exige ``puntaje`` y ``nivel_alcanzado``;
        en ``PATCH`` permite una actualización parcial.
        """
        evaluacion = self.get_object()
        partial = request.method == 'PATCH'
        serializer = EvaluacionCalificarSerializer(
            evaluacion, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                'message': 'Evaluación calificada con éxito',
                'data': EvaluacionListSerializer(evaluacion).data,
            },
            status=status.HTTP_200_OK,
        )
