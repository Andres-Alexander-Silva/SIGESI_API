from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import PerfilInvestigativo, User
from apps.sigesi.serializers.core.perfil_investigativo_serializer import (
    PerfilInvestigativoListSerializer,
    PerfilInvestigativoCreateUpdateSerializer,
)
from apps.sigesi.decorators.permissions import PerfilInvestigativoRolePermission


class PerfilInvestigativoViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para los perfiles investigativos de los estudiantes.

    El listado admite el filtro opcional ``?estudiante=``. El control de acceso
    por rol lo aplican ``PerfilInvestigativoRolePermission`` (a nivel de
    método/objeto) y ``get_queryset`` (alcance por filas): el Administrador tiene
    CRUD completo, el Director de Grupo solo lee los perfiles de los estudiantes
    matriculados en semilleros de su grupo, el Director de Semillero solo lee los
    de los estudiantes matriculados en su semillero, y el Estudiante / Líder
    Estudiantil solo leen su propio perfil.
    """

    queryset = (
        PerfilInvestigativo.objects.all()
        .select_related('estudiante', 'estudiante__programa_academico')
    )
    permission_classes = [PerfilInvestigativoRolePermission]
    filterset_fields = ['estudiante']

    def get_serializer_class(self):
        """Usa el serializador de escritura en create/update y el de lectura en el resto."""
        if self.action in ['create', 'update', 'partial_update']:
            return PerfilInvestigativoCreateUpdateSerializer
        return PerfilInvestigativoListSerializer

    def get_queryset(self):
        """Filtra los perfiles investigativos según el rol del usuario autenticado."""
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_authenticated:
            return queryset.none()

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return queryset

        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return queryset.filter(
                estudiante__matriculas_semillero__semillero__grupo_investigacion__director=user
            ).distinct()

        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return queryset.filter(
                estudiante__matriculas_semillero__semillero__director=user
            ).distinct()

        # Estudiante y Líder Estudiantil: solo su propio perfil.
        if user.tiene_alguno_de([
            User.RolChoices.ESTUDIANTE,
            User.RolChoices.LIDER_ESTUDIANTIL,
        ]):
            return queryset.filter(estudiante=user)

        return queryset.none()

    @swagger_auto_schema(
        operation_summary='Listar perfiles investigativos',
        operation_description=(
            'Retorna los perfiles investigativos visibles para el usuario '
            'autenticado. Admite el filtro opcional `estudiante`.'
        ),
        manual_parameters=[
            openapi.Parameter(
                'estudiante', openapi.IN_QUERY,
                description='Filtrar por ID de estudiante.',
                type=openapi.TYPE_INTEGER, required=False,
            ),
        ],
        responses={200: PerfilInvestigativoListSerializer(many=True)},
        tags=['Perfiles Investigativos'],
    )
    def list(self, request, *args, **kwargs):
        """Lista los perfiles investigativos visibles para el usuario."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Consultar detalle de perfil investigativo',
        responses={200: PerfilInvestigativoListSerializer, 404: 'Perfil no encontrado'},
        tags=['Perfiles Investigativos'],
    )
    def retrieve(self, request, *args, **kwargs):
        """Devuelve el detalle de un perfil, incluyendo el estudiante."""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Crear perfil investigativo',
        request_body=PerfilInvestigativoCreateUpdateSerializer,
        responses={
            201: PerfilInvestigativoListSerializer,
            400: openapi.Response('Errores de validación'),
            403: openapi.Response('No tiene permisos'),
        },
        tags=['Perfiles Investigativos'],
    )
    def create(self, request, *args, **kwargs):
        """Crea un perfil investigativo y responde con su representación de lectura."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        perfil = serializer.save()
        return Response(
            {
                'message': 'Perfil investigativo creado con éxito',
                'data': PerfilInvestigativoListSerializer(perfil).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Actualizar perfil investigativo',
        request_body=PerfilInvestigativoCreateUpdateSerializer,
        responses={
            200: PerfilInvestigativoListSerializer,
            400: 'Errores de validación',
            403: 'No tiene permisos',
            404: 'Perfil no encontrado',
        },
        tags=['Perfiles Investigativos'],
    )
    def update(self, request, *args, **kwargs):
        """Actualiza por completo un perfil investigativo."""
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Actualizar perfil investigativo (parcial)',
        request_body=PerfilInvestigativoCreateUpdateSerializer,
        responses={
            200: PerfilInvestigativoListSerializer,
            400: 'Errores de validación',
            403: 'No tiene permisos',
            404: 'Perfil no encontrado',
        },
        tags=['Perfiles Investigativos'],
    )
    def partial_update(self, request, *args, **kwargs):
        """Actualiza parcialmente un perfil investigativo."""
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Eliminar perfil investigativo',
        responses={
            204: openapi.Response('Perfil eliminado correctamente'),
            403: openapi.Response('No tiene permisos'),
            404: openapi.Response('Perfil no encontrado'),
        },
        tags=['Perfiles Investigativos'],
    )
    def destroy(self, request, *args, **kwargs):
        """Elimina un perfil investigativo."""
        return super().destroy(request, *args, **kwargs)
