from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from apps.sigesi.models import Proyecto, User
from apps.sigesi.serializers.core.proyecto_serializer import (
    ProyectoListSerializer,
    ProyectoCreateUpdateSerializer,
    ProyectoChangeStateSerializer
)
from apps.sigesi.decorators.permissions import ProyectoRolePermission


class ProyectoViewSet(viewsets.ModelViewSet):
    """
    ViewSet CRUD para la gestión de Proyectos.
    Integra control de acceso por roles y eliminación lógica segura.
    """
    queryset = Proyecto.objects.filter(is_active=True).order_by('-created_at')
    permission_classes = [ProyectoRolePermission]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProyectoCreateUpdateSerializer
        if self.action == 'change_state':
            return ProyectoChangeStateSerializer
        return ProyectoListSerializer

    def get_queryset(self):
        """
        Filtra los proyectos según el rol del usuario autenticado.
        """
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_authenticated:
            return queryset.none()

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return queryset

        if user.tiene_alguno_de([User.RolChoices.DIRECTOR_SEMILLERO, User.RolChoices.DIRECTOR_GRUPO]):
            # Retorna proyectos donde sea el director, o proyectos de semilleros que dirige
            return queryset.filter(
                models.Q(director=user) |
                models.Q(semilleros__director=user) |
                models.Q(semilleros__grupo_investigacion__director=user)
            ).distinct()

        if user.tiene_alguno_de([User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL]):
            # Retorna proyectos donde es líder o estudiante vinculado
            return queryset.filter(
                models.Q(lider=user) |
                models.Q(estudiantes=user)
            ).distinct()

        return queryset.none()

    @swagger_auto_schema(
        operation_summary="Listar proyectos",
        operation_description="Retorna la lista de proyectos permitidos para el usuario autenticado.",
        responses={200: ProyectoListSerializer(many=True)},
        tags=["Proyectos"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Consultar detalle de proyecto",
        operation_description="Retorna la información detallada de un proyecto.",
        responses={200: ProyectoListSerializer, 404: "Proyecto no encontrado"},
        tags=["Proyectos"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Crear proyecto",
        operation_description="Crea un nuevo proyecto. Estudiantes solo pueden crear en estado Idea.",
        request_body=ProyectoCreateUpdateSerializer,
        responses={
            201: ProyectoListSerializer,
            400: openapi.Response("Errores de validación"),
            403: openapi.Response("No tiene permisos")
        },
        tags=["Proyectos"]
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proyecto = serializer.save()
        return Response(
            {'message': 'Proyecto creado con éxito', 'data': ProyectoListSerializer(proyecto).data},
            status=status.HTTP_201_CREATED
        )

    @swagger_auto_schema(
        operation_summary="Actualizar proyecto",
        operation_description="Actualiza la información del proyecto.",
        request_body=ProyectoCreateUpdateSerializer,
        responses={
            200: ProyectoListSerializer,
            400: "Errores de validación",
            403: "No tiene permisos para modificar",
            404: "Proyecto no encontrado"
        },
        tags=["Proyectos"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Actualizar proyecto (parcial)",
        operation_description="Actualiza campos específicos del proyecto.",
        request_body=ProyectoCreateUpdateSerializer,
        responses={
            200: ProyectoListSerializer,
            400: "Errores de validación",
            403: "No tiene permisos",
            404: "Proyecto no encontrado"
        },
        tags=["Proyectos"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Eliminar proyecto (lógico)",
        operation_description="Cambia el estado del proyecto a inactivo.",
        responses={
            204: openapi.Response("Proyecto inactivado correctamente"),
            403: openapi.Response("No tiene permisos"),
            404: openapi.Response("Proyecto no encontrado")
        },
        tags=["Proyectos"]
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_summary="Cambiar estado del proyecto",
        operation_description="Permite a Directores y Administradores cambiar el estado de un proyecto.",
        request_body=ProyectoChangeStateSerializer,
        responses={
            200: ProyectoListSerializer,
            400: "Errores de validación",
            403: "No tiene permisos (ej. Estudiante intentando cambiar estado)",
            404: "Proyecto no encontrado"
        },
        tags=["Proyectos"]
    )
    @action(detail=True, methods=['patch'], url_path='change_state')
    def change_state(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        proyecto = serializer.save()
        return Response(
            {'message': 'Estado del proyecto actualizado', 'data': ProyectoListSerializer(proyecto).data},
            status=status.HTTP_200_OK
        )
