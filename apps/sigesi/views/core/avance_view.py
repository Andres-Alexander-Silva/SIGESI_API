from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import models as db_models
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import Avance, Proyecto, User
from apps.sigesi.serializers.core.avance_serializer import (
    AvanceListSerializer,
    AvanceCreateUpdateSerializer,
)
from apps.sigesi.filters.core.avance_filter import AvanceFilter
from apps.sigesi.decorators.permissions import AvanceRolePermission


class AvanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet CRUD para la gestión de Avances de Proyecto.

    Soporta carga de evidencias (multipart/form-data) en la creación y
    actualización.  Aplica control de acceso por rol en todos los endpoints.

    Filtros disponibles en GET /avances:
      ?proyecto_id=<id>        – avances de un proyecto (canónico)
      ?usuario_id=<id>         – avances de un usuario en un proyecto (canónico)
      ?proyecto=<id>           – alias de proyecto_id (backward-compat)
      ?registrado_por=<id>     – alias de usuario_id  (backward-compat)
      ?estado=<val>            – filtra por estado del avance
      ?fecha_desde=YYYY-MM-DD  – avances desde esta fecha
      ?fecha_hasta=YYYY-MM-DD  – avances hasta esta fecha

    Validaciones en GET /avances:
      • proyecto_id debe referenciar un proyecto existente → 404
      • usuario_id debe referenciar un usuario existente  → 404
      • el usuario referenciado debe pertenecer al proyecto → 400
      • un estudiante no puede filtrar por otro usuario_id → 403
    """

    permission_classes = [AvanceRolePermission]
    filterset_class    = AvanceFilter

    def get_queryset(self):
        """
        Retorna el queryset base filtrado según el rol del usuario autenticado.

        • Administrador        → todos los avances.
        • Director de Grupo    → avances de proyectos de semilleros de su grupo.
        • Director de Semillero→ avances de proyectos de su semillero.
        • Líder Estudiantil    → avances de proyectos donde es líder.
        • Estudiante           → únicamente sus propios avances.
        """
        user = self.request.user

        if not user.is_authenticated:
            return Avance.objects.none()

        base_qs = (
            Avance.objects
            .select_related('proyecto', 'registrado_por')
            .prefetch_related('evidencias', 'evidencias__subido_por')
            .order_by('-fecha')
        )

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return base_qs

        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return base_qs.filter(
                proyecto__semilleros__grupo_investigacion__director=user
            ).distinct()

        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return base_qs.filter(
                db_models.Q(proyecto__director=user)
                | db_models.Q(proyecto__semilleros__director=user)
            ).distinct()

        if user.tiene_rol(User.RolChoices.LIDER_ESTUDIANTIL):
            return base_qs.filter(
                db_models.Q(proyecto__lider=user)
                | db_models.Q(proyecto__estudiantes=user)
            ).distinct()

        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return base_qs.filter(registrado_por=user)

        return Avance.objects.none()

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return AvanceCreateUpdateSerializer
        return AvanceListSerializer

    # ------------------------------------------------------------------
    # Swagger docs
    # ------------------------------------------------------------------

    # ── Parámetros Swagger para el listado filtrado ───────────────────────
    _list_query_params = [
        openapi.Parameter(
            'proyecto_id', openapi.IN_QUERY,
            description='ID del proyecto a consultar.',
            type=openapi.TYPE_INTEGER,
        ),
        openapi.Parameter(
            'usuario_id', openapi.IN_QUERY,
            description='ID del usuario (registrador) a filtrar dentro del proyecto.',
            type=openapi.TYPE_INTEGER,
        ),
        openapi.Parameter(
            'estado', openapi.IN_QUERY,
            description='Estado del avance: borrador | enviado | revisado | aprobado | rechazado.',
            type=openapi.TYPE_STRING,
        ),
        openapi.Parameter(
            'fecha_desde', openapi.IN_QUERY,
            description='Fecha mínima del avance (YYYY-MM-DD).',
            type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE,
        ),
        openapi.Parameter(
            'fecha_hasta', openapi.IN_QUERY,
            description='Fecha máxima del avance (YYYY-MM-DD).',
            type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE,
        ),
    ]

    @swagger_auto_schema(
        operation_summary="Listar avances con filtros por proyecto y usuario",
        operation_description=(
            "Retorna la lista de avances permitidos para el usuario autenticado.\n\n"
            "**Casos de uso:**\n"
            "- Avances de un proyecto: `?proyecto_id={id}`\n"
            "- Avances de un estudiante en un proyecto: `?proyecto_id={id}&usuario_id={id}`\n\n"
            "**Protecciones:**\n"
            "- `proyecto_id` debe existir en base de datos (→ 404 si no).\n"
            "- `usuario_id` debe existir y pertenecer al proyecto (→ 404 / 400).\n"
            "- Un estudiante **no puede** filtrar por `usuario_id` ajeno (→ 403).\n"
            "- Cada rol recibe únicamente los avances que le corresponden según visibilidad."
        ),
        manual_parameters=_list_query_params,
        responses={
            200: AvanceListSerializer(many=True),
            400: openapi.Response("usuario_id no pertenece al proyecto indicado"),
            401: openapi.Response("Token JWT inválido o ausente"),
            403: openapi.Response("Sin permisos para ver avances de ese usuario"),
            404: openapi.Response("Proyecto o usuario no encontrado"),
        },
        tags=["Avances"],
    )
    def list(self, request, *args, **kwargs):
        """
        Lista de avances con validaciones de existencia, pertenencia y visibilidad.

        Flujo de validación:
          1. Si se recibe `proyecto_id`, verificar que el proyecto exista.
          2. Si se recibe `usuario_id`, verificar que el usuario exista.
          3. Si ambos están presentes, verificar que el usuario pertenezca al proyecto.
          4. Si el solicitante es Estudiante y el `usuario_id` no es el suyo → 403.
          5. El queryset ya aplica el filtro RBAC antes de llegar al filterset.
        """
        proyecto_id = request.query_params.get('proyecto_id') or request.query_params.get('proyecto')
        usuario_id  = request.query_params.get('usuario_id')  or request.query_params.get('registrado_por')
        auth_user   = request.user

        # ── 1. Validar existencia del proyecto ───────────────────────────
        proyecto = None
        if proyecto_id:
            try:
                proyecto = Proyecto.objects.get(pk=proyecto_id)
            except (Proyecto.DoesNotExist, ValueError):
                return Response(
                    {'message': f'El proyecto con id={proyecto_id} no existe.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # ── 2. Validar existencia del usuario ────────────────────────────
        usuario_filtrado = None
        if usuario_id:
            try:
                usuario_filtrado = User.objects.get(pk=usuario_id)
            except (User.DoesNotExist, ValueError):
                return Response(
                    {'message': f'El usuario con id={usuario_id} no existe.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # ── 3. Validar pertenencia del usuario al proyecto ───────────────
        if proyecto and usuario_filtrado:
            pertenece = (
                proyecto.director == usuario_filtrado
                or proyecto.lider  == usuario_filtrado
                or proyecto.estudiantes.filter(pk=usuario_filtrado.pk).exists()
                or proyecto.semilleros.filter(director=usuario_filtrado).exists()
                or proyecto.semilleros.filter(
                    grupo_investigacion__director=usuario_filtrado
                ).exists()
            )
            if not pertenece:
                return Response(
                    {
                        'message': (
                            f'El usuario id={usuario_id} no pertenece al '
                            f'proyecto id={proyecto_id}.'
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ── 4. Estudiante intentando ver avances de otro usuario ─────────
        if usuario_filtrado and auth_user.tiene_rol(User.RolChoices.ESTUDIANTE):
            if usuario_filtrado.pk != auth_user.pk:
                return Response(
                    {'message': 'No tienes permiso para consultar avances de otros usuarios.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # ── 5. Delegar al comportamiento estándar (queryset RBAC + filterset) ─
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Consultar detalle de avance",
        operation_description="Retorna la información completa de un avance, incluidas sus evidencias.",
        responses={
            200: AvanceListSerializer,
            403: openapi.Response("Sin permiso para ver este avance"),
            404: openapi.Response("Avance no encontrado"),
        },
        tags=["Avances"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Crear avance (con evidencia opcional)",
        operation_description=(
            "Crea un nuevo avance de proyecto. Enviar como **multipart/form-data** "
            "para adjuntar un archivo de evidencia.\n\n"
            "**Tipos de archivo permitidos:** PDF, JPG, PNG, DOCX.\n"
            "**Tamaño máximo:** 5 MB.\n\n"
            "Campos de evidencia (opcionales):\n"
            "- `archivo`: archivo binario\n"
            "- `titulo_evidencia`: título de la evidencia\n"
            "- `descripcion_evidencia`: descripción de la evidencia"
        ),
        request_body=AvanceCreateUpdateSerializer,
        responses={
            201: AvanceListSerializer,
            400: openapi.Response("Errores de validación (campos o archivo inválido)"),
            401: openapi.Response("Token JWT inválido o ausente"),
            403: openapi.Response("Sin permisos o no pertenece al proyecto"),
        },
        tags=["Avances"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        avance = serializer.save()
        return Response(
            {
                'message': 'Avance creado con éxito.',
                'data': AvanceListSerializer(avance, context={'request': request}).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="Actualización completa de avance",
        operation_description=(
            "Actualiza todos los campos de un avance. Enviar como **multipart/form-data** "
            "para adjuntar un nuevo archivo de evidencia."
        ),
        request_body=AvanceCreateUpdateSerializer,
        responses={
            200: AvanceListSerializer,
            400: openapi.Response("Errores de validación"),
            401: openapi.Response("No autenticado"),
            403: openapi.Response("Sin permisos para modificar este avance"),
            404: openapi.Response("Avance no encontrado"),
        },
        tags=["Avances"],
    )
    def update(self, request, *args, **kwargs):
        kwargs['partial'] = False
        return self._update_avance(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Actualización parcial de avance",
        operation_description=(
            "Actualiza campos específicos de un avance. Los directores pueden usar "
            "este endpoint para agregar observaciones sin modificar el resto del avance."
        ),
        request_body=AvanceCreateUpdateSerializer,
        responses={
            200: AvanceListSerializer,
            400: openapi.Response("Errores de validación"),
            401: openapi.Response("No autenticado"),
            403: openapi.Response("Sin permisos"),
            404: openapi.Response("Avance no encontrado"),
        },
        tags=["Avances"],
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self._update_avance(request, *args, **kwargs)

    def _update_avance(self, request, *args, **kwargs):
        """Lógica compartida para PUT y PATCH con respuesta enriquecida."""
        partial  = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        avance = serializer.save()
        return Response(
            {
                'message': 'Avance actualizado con éxito.',
                'data': AvanceListSerializer(avance, context={'request': request}).data,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_summary="Eliminar avance",
        operation_description=(
            "Elimina un avance **únicamente si no tiene evidencias asociadas**. "
            "Los estudiantes no pueden eliminar avances. "
            "El administrador puede eliminar sin restricción de evidencias."
        ),
        responses={
            204: openapi.Response("Avance eliminado correctamente"),
            401: openapi.Response("No autenticado"),
            403: openapi.Response("Sin permisos o el avance tiene evidencias asociadas"),
            404: openapi.Response("Avance no encontrado"),
        },
        tags=["Avances"],
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Bloqueo adicional en la vista para devolver 409 en lugar de 403
        # cuando el avance tiene evidencias (ya controlado por el permiso,
        # pero devolvemos un mensaje más descriptivo aquí).
        user = request.user
        if not user.tiene_rol(User.RolChoices.ADMINISTRADOR) and instance.evidencias.exists():
            return Response(
                {
                    'message': (
                        'No se puede eliminar el avance porque tiene evidencias asociadas. '
                        'Elimine primero las evidencias antes de borrar el avance.'
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
