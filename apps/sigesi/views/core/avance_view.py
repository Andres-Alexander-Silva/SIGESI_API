from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import models as db_models
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import Avance, User
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
      ?proyecto=<id>  – filtra por ID de proyecto
      ?estado=<val>   – filtra por estado del avance
      ?fecha_desde=YYYY-MM-DD  – avances desde esta fecha
      ?fecha_hasta=YYYY-MM-DD  – avances hasta esta fecha
      ?registrado_por=<id>     – filtra por usuario que registró el avance
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

    @swagger_auto_schema(
        operation_summary="Listar avances",
        operation_description=(
            "Retorna la lista de avances permitidos para el usuario autenticado. "
            "Soporta filtros: ?proyecto, ?estado, ?fecha_desde, ?fecha_hasta, ?registrado_por."
        ),
        responses={200: AvanceListSerializer(many=True)},
        tags=["Avances"],
    )
    def list(self, request, *args, **kwargs):
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
