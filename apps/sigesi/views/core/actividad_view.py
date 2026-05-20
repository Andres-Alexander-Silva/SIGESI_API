from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import models

from apps.sigesi.models import Actividad, User
from apps.sigesi.serializers.core.actividad_serializer import (
    ActividadListSerializer,
    ActividadCreateUpdateSerializer
)
from apps.sigesi.decorators.permissions import ActividadRolePermission


class ActividadViewSet(viewsets.ModelViewSet):
    """
    ViewSet CRUD para la gestión de Actividades.
    Integra control de acceso por roles.
    """
    queryset = Actividad.objects.all().select_related('proyecto', 'responsable').order_by('fecha_inicio')
    permission_classes = [ActividadRolePermission]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ActividadCreateUpdateSerializer
        return ActividadListSerializer

    def get_queryset(self):
        """
        Filtra las actividades según el rol del usuario autenticado.
        """
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_authenticated:
            return queryset.none()

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return queryset

        # Directores de Semillero/Grupo: ven actividades de los proyectos de sus semilleros
        if user.tiene_alguno_de([User.RolChoices.DIRECTOR_SEMILLERO, User.RolChoices.DIRECTOR_GRUPO]):
            return queryset.filter(
                models.Q(proyecto__director=user) |
                models.Q(proyecto__semilleros__director=user) |
                models.Q(proyecto__semilleros__grupo_investigacion__director=user)
            ).distinct()

        # Estudiantes o Líderes Estudiantiles: ven actividades donde son responsables o de proyectos donde están vinculados
        if user.tiene_alguno_de([User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL]):
            return queryset.filter(
                models.Q(responsable=user) |
                models.Q(proyecto__lider=user) |
                models.Q(proyecto__estudiantes=user)
            ).distinct()

        return queryset.none()

    @swagger_auto_schema(
        operation_summary="Listar actividades",
        operation_description="Retorna la lista de actividades permitidas para el usuario autenticado.",
        responses={200: ActividadListSerializer(many=True)},
        tags=["Actividades"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Consultar detalle de actividad",
        operation_description="Retorna la información detallada de una actividad.",
        responses={200: ActividadListSerializer, 404: "Actividad no encontrada"},
        tags=["Actividades"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Crear actividad",
        operation_description="Crea una nueva actividad.",
        request_body=ActividadCreateUpdateSerializer,
        responses={
            201: ActividadListSerializer,
            400: openapi.Response("Errores de validación"),
            403: openapi.Response("No tiene permisos")
        },
        tags=["Actividades"]
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not request.data.get('porcentaje_avance'):
            request.data['porcentaje_avance'] = 0
        serializer.is_valid(raise_exception=True)
        actividad = serializer.save()
        return Response(
            {'message': 'Actividad creada con éxito', 'data': ActividadListSerializer(actividad).data},
            status=status.HTTP_201_CREATED
        )

    @swagger_auto_schema(
        operation_summary="Actualizar actividad",
        operation_description="Actualiza la información completa de una actividad.",
        request_body=ActividadCreateUpdateSerializer,
        responses={
            200: ActividadListSerializer,
            400: "Errores de validación",
            403: "No tiene permisos para modificar",
            404: "Actividad no encontrada"
        },
        tags=["Actividades"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Actualizar actividad (parcial)",
        operation_description="Actualiza campos específicos de una actividad.",
        request_body=ActividadCreateUpdateSerializer,
        responses={
            200: ActividadListSerializer,
            400: "Errores de validación",
            403: "No tiene permisos",
            404: "Actividad no encontrada"
        },
        tags=["Actividades"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Eliminar actividad",
        operation_description="Elimina una actividad (eliminación física).",
        responses={
            204: openapi.Response("Actividad eliminada correctamente"),
            403: openapi.Response("No tiene permisos"),
            404: openapi.Response("Actividad no encontrada")
        },
        tags=["Actividades"]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
