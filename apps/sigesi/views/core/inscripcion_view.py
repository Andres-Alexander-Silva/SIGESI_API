from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q
from apps.sigesi.models import MatriculaSemillero, User
from apps.sigesi.serializers.core.inscripcion_serializer import (
    InscripcionListSerializer,
    InscripcionCreateSerializer,
)
from apps.sigesi.decorators.permissions import InscripcionRolePermission
from apps.sigesi.utils.alcance import semilleros_en_alcance


class InscripcionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la gestión de inscripciones de estudiantes en semilleros.
    Soporta: listar, consultar detalle, crear inscripción y retirarse (eliminación lógica).
    No soporta actualización (PUT/PATCH).
    """
    permission_classes = [InscripcionRolePermission]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'create':
            return InscripcionCreateSerializer
        return InscripcionListSerializer

    def get_queryset(self):
        user = self.request.user

        if not user or not user.is_authenticated:
            return MatriculaSemillero.objects.none()

        # Filtrado de queryset según el alcance del usuario.
        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            qs = MatriculaSemillero.objects.all()
        else:
            # Gestores (director de grupo/semillero, líder) ven las matrículas de
            # los semilleros de su alcance; además, todos ven las propias.
            qs = MatriculaSemillero.objects.filter(
                Q(semillero__in=semilleros_en_alcance(user))
                | Q(estudiante=user)
            )

        # Filtro opcional por semillero
        semillero_id = self.request.query_params.get('semillero_id')
        if semillero_id:
            qs = qs.filter(semillero_id=semillero_id)

        return qs.select_related('estudiante', 'semillero').order_by('-created_at')

    # ----- LIST -----
    @swagger_auto_schema(
        operation_summary="Listar inscripciones",
        operation_description=(
            "Retorna las inscripciones de semillero según el rol del usuario autenticado.\n"
            "- Estudiante: solo sus inscripciones.\n"
            "- Director de Semillero: inscripciones de su semillero.\n"
            "- Director de Grupo / Administrador: todas.\n\n"
            "Parámetro opcional: `semillero_id` para filtrar por semillero."
        ),
        manual_parameters=[
            openapi.Parameter(
                'semillero_id', openapi.IN_QUERY,
                description='ID del semillero para filtrar inscripciones',
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={200: InscripcionListSerializer(many=True)},
        tags=["Inscripciones"],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # ----- RETRIEVE -----
    @swagger_auto_schema(
        operation_summary="Consultar detalle de inscripción",
        operation_description="Retorna la información detallada de una inscripción específica.",
        responses={
            200: InscripcionListSerializer,
            403: "No tiene permisos para ver esta inscripción",
            404: "Inscripción no encontrada",
        },
        tags=["Inscripciones"],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = InscripcionListSerializer(instance)
        return Response(serializer.data)

    # ----- CREATE -----
    @swagger_auto_schema(
        operation_summary="Crear inscripción (unirse a semillero)",
        operation_description=(
            "Inscribe a un estudiante en un semillero para un semestre dado.\n\n"
            "- Si el usuario es **estudiante**, el campo `estudiante` es opcional "
            "(se auto-asigna al usuario autenticado).\n"
            "- Si el usuario es **director de semillero** o **administrador**, "
            "debe enviar el campo `estudiante` con el ID del estudiante a inscribir.\n\n"
            "**Rol dentro del semillero** (`rol_en_semillero`): `estudiante` (por defecto) "
            "o `lider_estudiantil`. Designar líder solo lo permite un administrador, el "
            "director del semillero o un director de grupo. Al designar un nuevo líder, "
            "este pasa a ser el `lider_estudiantil` del semillero (y gana ese rol global); "
            "el líder anterior conserva su inscripción como estudiante."
        ),
        request_body=InscripcionCreateSerializer,
        responses={
            201: openapi.Response("Inscripción creada con éxito", InscripcionListSerializer),
            400: openapi.Response("Errores de validación (duplicado, semillero inactivo, etc.)"),
            403: openapi.Response("No tiene permisos para realizar esta acción"),
        },
        tags=["Inscripciones"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        inscripcion = serializer.save()
        return Response(
            {
                'message': 'Inscripción creada con éxito.',
                'data': InscripcionListSerializer(inscripcion).data,
            },
            status=status.HTTP_201_CREATED,
        )

    # ----- DESTROY (retiro lógico) -----
    @swagger_auto_schema(
        operation_summary="Retirar inscripción (retiro lógico)",
        operation_description=(
            "Cambia el estado de la inscripción a 'retirado'.\n"
            "Solo se puede retirar una inscripción que esté en estado 'activa'."
        ),
        responses={
            200: openapi.Response("Inscripción retirada correctamente"),
            400: openapi.Response("La inscripción no se encuentra en estado activa"),
            403: openapi.Response("No tiene permisos para retirar esta inscripción"),
            404: openapi.Response("Inscripción no encontrada"),
        },
        tags=["Inscripciones"],
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.estado != MatriculaSemillero.EstadoChoices.ACTIVA:
            return Response(
                {'error': 'Solo se puede retirar una inscripción que esté en estado activa.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.estado = MatriculaSemillero.EstadoChoices.RETIRADO
        instance.save(update_fields=['estado', 'updated_at'])

        return Response(
            {'message': 'Te has retirado del semillero exitosamente.'},
            status=status.HTTP_200_OK,
        )
