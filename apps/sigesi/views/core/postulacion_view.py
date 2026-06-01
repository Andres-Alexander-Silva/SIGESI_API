from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from apps.sigesi.models import Postulacion, User
from apps.sigesi.serializers.core.postulacion_serializer import (
    PostulacionListSerializer,
    PostulacionCreateUpdateSerializer,
)
from apps.sigesi.decorators.permissions import PostulacionRolePermission


class PostulacionViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para las postulaciones de semilleros a convocatorias.

    Control de acceso (ver :class:`PostulacionRolePermission`):
    - Administrador: CRUD total y resolución.
    - Director de Semillero: crea/edita/elimina postulaciones de su semillero.
    - Director de Grupo: lectura + resolución (``aprobar``/``rechazar``) de las
      postulaciones de los semilleros de su grupo.
    - Líder Estudiantil / Estudiante: solo lectura (de su semillero / propias).

    El alcance por filas lo aplica ``get_queryset``. Admite filtrar por
    ``convocatoria``, ``semillero`` y ``estado``.
    """

    queryset = (
        Postulacion.objects.all()
        .select_related(
            'convocatoria',
            'convocatoria__evento',
            'semillero',
            'semillero__grupo_investigacion',
            'proyecto',
            'aprobado_por',
        )
        .prefetch_related('estudiantes')
    )
    permission_classes = [PostulacionRolePermission]
    filterset_fields = ['convocatoria', 'semillero', 'estado']

    def get_serializer_class(self):
        """Usa el serializador de escritura en create/update y el de lectura en el resto."""
        if self.action in ['create', 'update', 'partial_update']:
            return PostulacionCreateUpdateSerializer
        return PostulacionListSerializer

    def get_queryset(self):
        """Filtra las postulaciones según el rol del usuario autenticado."""
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_authenticated:
            return queryset.none()

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return queryset

        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return queryset.filter(
                semillero__grupo_investigacion__director=user).distinct()

        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return queryset.filter(semillero__director=user).distinct()

        if user.tiene_rol(User.RolChoices.LIDER_ESTUDIANTIL):
            return queryset.filter(semillero__lider_estudiantil=user).distinct()

        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return queryset.filter(estudiantes=user).distinct()

        return queryset.none()

    @swagger_auto_schema(
        operation_summary='Listar postulaciones',
        manual_parameters=[
            openapi.Parameter('convocatoria', openapi.IN_QUERY, description='Filtrar por ID de convocatoria.',
                              type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('semillero', openapi.IN_QUERY, description='Filtrar por ID de semillero.',
                              type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('estado', openapi.IN_QUERY, description='Filtrar por estado.',
                              type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: PostulacionListSerializer(many=True)},
        tags=['Postulaciones'],
    )
    def list(self, request, *args, **kwargs):
        """Lista las postulaciones visibles para el usuario."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Consultar detalle de postulación',
        responses={200: PostulacionListSerializer, 404: 'Postulación no encontrada'},
        tags=['Postulaciones'],
    )
    def retrieve(self, request, *args, **kwargs):
        """Devuelve el detalle de una postulación."""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Registrar postulación',
        request_body=PostulacionCreateUpdateSerializer,
        responses={
            201: PostulacionListSerializer,
            400: openapi.Response('Errores de validación (aval, semillero ajeno, estudiante no matriculado, convocatoria cerrada)'),
            403: openapi.Response('No tiene permisos'),
        },
        tags=['Postulaciones'],
    )
    def create(self, request, *args, **kwargs):
        """Registra una postulación y responde con su representación de lectura."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        postulacion = serializer.save()
        return Response(
            {
                'message': 'Postulación registrada con éxito',
                'data': PostulacionListSerializer(postulacion).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Actualizar postulación',
        request_body=PostulacionCreateUpdateSerializer,
        responses={200: PostulacionListSerializer, 400: 'Errores de validación',
                   403: 'No tiene permisos', 404: 'Postulación no encontrada'},
        tags=['Postulaciones'],
    )
    def update(self, request, *args, **kwargs):
        """Actualiza por completo una postulación."""
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Actualizar postulación (parcial)',
        request_body=PostulacionCreateUpdateSerializer,
        responses={200: PostulacionListSerializer, 400: 'Errores de validación',
                   403: 'No tiene permisos', 404: 'Postulación no encontrada'},
        tags=['Postulaciones'],
    )
    def partial_update(self, request, *args, **kwargs):
        """Actualiza parcialmente una postulación."""
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Eliminar postulación',
        responses={204: openapi.Response('Postulación eliminada correctamente'),
                   403: openapi.Response('No tiene permisos'),
                   404: openapi.Response('Postulación no encontrada')},
        tags=['Postulaciones'],
    )
    def destroy(self, request, *args, **kwargs):
        """Elimina una postulación."""
        return super().destroy(request, *args, **kwargs)

    def _resolver(self, request, nuevo_estado):
        """Resuelve la postulación (aprobar/rechazar): valida rol, estado y sella auditoría.

        Solo Administrador y Director de Grupo pueden resolver; ``get_object()``
        aplica el filtro de queryset y ``has_object_permission`` (el Director de
        Grupo solo alcanza postulaciones de su grupo). Sella ``estado``,
        ``aprobado_por`` y ``fecha_resolucion``, y guarda ``resultado``/
        ``observaciones`` opcionales del cuerpo. Devuelve un ``Response``.
        """
        user = request.user

        if not user.tiene_alguno_de([
            User.RolChoices.ADMINISTRADOR,
            User.RolChoices.DIRECTOR_GRUPO,
        ]):
            return Response(
                {'error': 'Solo el Administrador o el Director de Grupo pueden resolver una postulación.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        postulacion = self.get_object()

        if postulacion.estado == nuevo_estado:
            return Response(
                {'error': f'La postulación ya está en estado "{nuevo_estado}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        postulacion.estado = nuevo_estado
        postulacion.aprobado_por = user
        postulacion.fecha_resolucion = timezone.now()
        if 'resultado' in request.data:
            postulacion.resultado = request.data.get('resultado', '')
        if 'observaciones' in request.data:
            postulacion.observaciones = request.data.get('observaciones', '')
        postulacion.save(update_fields=[
            'estado', 'aprobado_por', 'fecha_resolucion', 'resultado',
            'observaciones', 'updated_at',
        ])
        return postulacion

    @swagger_auto_schema(
        operation_summary='Aprobar (aceptar) postulación',
        operation_description=(
            'Acepta la postulación. Solo Administrador y Director de Grupo (del '
            'grupo del semillero). Marca `estado=aceptada`, sella `aprobado_por` '
            'y `fecha_resolucion`. Acepta `resultado`/`observaciones` opcionales.'
        ),
        request_body=no_body,
        responses={
            200: PostulacionListSerializer,
            400: openapi.Response('La postulación ya está aceptada'),
            403: openapi.Response('No tiene permisos para resolver'),
            404: openapi.Response('Postulación no encontrada'),
        },
        tags=['Postulaciones'],
    )
    @action(detail=True, methods=['post'], url_path='aprobar')
    def aprobar(self, request, pk=None):
        """Acepta una postulación (solo Administrador / Director de Grupo)."""
        resultado = self._resolver(request, Postulacion.EstadoChoices.ACEPTADA)
        if isinstance(resultado, Response):
            return resultado
        return Response(
            {
                'message': 'Postulación aceptada con éxito',
                'data': PostulacionListSerializer(resultado).data,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_summary='Rechazar postulación',
        operation_description=(
            'Rechaza la postulación. Solo Administrador y Director de Grupo (del '
            'grupo del semillero). Marca `estado=rechazada`, sella `aprobado_por` '
            'y `fecha_resolucion`. Acepta `resultado`/`observaciones` opcionales.'
        ),
        request_body=no_body,
        responses={
            200: PostulacionListSerializer,
            400: openapi.Response('La postulación ya está rechazada'),
            403: openapi.Response('No tiene permisos para resolver'),
            404: openapi.Response('Postulación no encontrada'),
        },
        tags=['Postulaciones'],
    )
    @action(detail=True, methods=['post'], url_path='rechazar')
    def rechazar(self, request, pk=None):
        """Rechaza una postulación (solo Administrador / Director de Grupo)."""
        resultado = self._resolver(request, Postulacion.EstadoChoices.RECHAZADA)
        if isinstance(resultado, Response):
            return resultado
        return Response(
            {
                'message': 'Postulación rechazada con éxito',
                'data': PostulacionListSerializer(resultado).data,
            },
            status=status.HTTP_200_OK,
        )
