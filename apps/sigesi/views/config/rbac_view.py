from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from apps.sigesi.models import Menu, Opcion, Permiso
from apps.sigesi.serializers.config.rbac_serializer import MenuSerializer, OpcionSerializer, PermisoSerializer
from apps.sigesi.utils.notifications import notificar_cambio_permiso, notificar_cambios_permisos_multiples
from django.contrib.auth import get_user_model

User = get_user_model()


class MenuViewSet(viewsets.ModelViewSet):
    """
    ViewSet para realizar operaciones CRUD completas sobre los Menús.
    """
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Listar menús",
        operation_description="Retorna la lista de todos los menús registrados en el sistema.",
        responses={
            200: MenuSerializer(many=True),
            401: openapi.Response("No autenticado"),
        },
        tags=["RBAC - Menús"],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Crear menú",
        operation_description="Crea un nuevo menú en el sistema. Se puede indicar un `menu_padre` para crear submenús.",
        request_body=MenuSerializer,
        responses={
            201: MenuSerializer,
            400: openapi.Response("Datos inválidos"),
            401: openapi.Response("No autenticado"),
        },
        tags=["RBAC - Menús"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Obtener menú",
        operation_description="Retorna el detalle de un menú específico por su ID.",
        responses={
            200: MenuSerializer,
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Menú no encontrado"),
        },
        tags=["RBAC - Menús"],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Actualizar menú (completo)",
        operation_description="Actualiza todos los campos de un menú existente.",
        request_body=MenuSerializer,
        responses={
            200: MenuSerializer,
            400: openapi.Response("Datos inválidos"),
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Menú no encontrado"),
        },
        tags=["RBAC - Menús"],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Actualizar menú (parcial)",
        operation_description="Actualiza uno o más campos de un menú existente sin necesidad de enviar todos los campos.",
        request_body=MenuSerializer,
        responses={
            200: MenuSerializer,
            400: openapi.Response("Datos inválidos"),
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Menú no encontrado"),
        },
        tags=["RBAC - Menús"],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Eliminar menú",
        operation_description="Elimina un menú del sistema. Si tiene submenús asociados, estos también serán eliminados (CASCADE).",
        responses={
            204: openapi.Response("Menú eliminado correctamente"),
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Menú no encontrado"),
        },
        tags=["RBAC - Menús"],
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OpcionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operaciones CRUD sobre Opciones (Acciones del sistema).
    """
    queryset = Opcion.objects.all()
    serializer_class = OpcionSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Listar opciones",
        operation_description="Retorna la lista de todas las opciones/acciones disponibles en el sistema (ver, crear, editar, eliminar, aprobar, exportar).",
        responses={
            200: OpcionSerializer(many=True),
            401: openapi.Response("No autenticado"),
        },
        tags=["RBAC - Opciones"],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Crear opción",
        operation_description=(
            "Crea una nueva opción asociada a un menú. El campo `accion` acepta los valores: "
            "`ver`, `crear`, `editar`, `eliminar`, `aprobar`, `exportar`. "
            "El campo `codigo` debe ser único en el sistema."
        ),
        request_body=OpcionSerializer,
        responses={
            201: OpcionSerializer,
            400: openapi.Response("Datos inválidos"),
            401: openapi.Response("No autenticado"),
        },
        tags=["RBAC - Opciones"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Obtener opción",
        operation_description="Retorna el detalle de una opción específica por su ID.",
        responses={
            200: OpcionSerializer,
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Opción no encontrada"),
        },
        tags=["RBAC - Opciones"],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Actualizar opción (completo)",
        operation_description="Actualiza todos los campos de una opción existente.",
        request_body=OpcionSerializer,
        responses={
            200: OpcionSerializer,
            400: openapi.Response("Datos inválidos"),
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Opción no encontrada"),
        },
        tags=["RBAC - Opciones"],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Actualizar opción (parcial)",
        operation_description="Actualiza uno o más campos de una opción existente.",
        request_body=OpcionSerializer,
        responses={
            200: OpcionSerializer,
            400: openapi.Response("Datos inválidos"),
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Opción no encontrada"),
        },
        tags=["RBAC - Opciones"],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Eliminar opción",
        operation_description="Elimina una opción del sistema. Los permisos asociados a esta opción también serán eliminados (CASCADE).",
        responses={
            204: openapi.Response("Opción eliminada correctamente"),
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Opción no encontrada"),
        },
        tags=["RBAC - Opciones"],
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PermisoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para administrar los Permisos (Asignación de 'Opciones' a 'Roles').
    """
    queryset = Permiso.objects.all()
    serializer_class = PermisoSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Listar permisos",
        operation_description="Retorna la lista de todos los permisos asignados. Cada permiso relaciona un `rol` con una `opcion` específica del sistema.",
        responses={
            200: PermisoSerializer(many=True),
            401: openapi.Response("No autenticado"),
        },
        tags=["RBAC - Permisos"],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Crear permiso",
        operation_description=(
            "Asigna una opción a un rol. El campo `rol` acepta: "
            "`administrador`, `director_grupo`, `director_semillero`, "
            "`lider_estudiantil`, `estudiante`, `comite`."
        ),
        request_body=PermisoSerializer,
        responses={
            201: PermisoSerializer,
            400: openapi.Response("Datos inválidos"),
            401: openapi.Response("No autenticado"),
        },
        tags=["RBAC - Permisos"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Obtener permiso",
        operation_description="Retorna el detalle de un permiso específico por su ID.",
        responses={
            200: PermisoSerializer,
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Permiso no encontrado"),
        },
        tags=["RBAC - Permisos"],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Actualizar permiso (completo)",
        operation_description="Actualiza todos los campos de un permiso existente.",
        request_body=PermisoSerializer,
        responses={
            200: PermisoSerializer,
            400: openapi.Response("Datos inválidos"),
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Permiso no encontrado"),
        },
        tags=["RBAC - Permisos"],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Actualizar permiso (parcial)",
        operation_description="Actualiza uno o más campos de un permiso existente.",
        request_body=PermisoSerializer,
        responses={
            200: PermisoSerializer,
            400: openapi.Response("Datos inválidos"),
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Permiso no encontrado"),
        },
        tags=["RBAC - Permisos"],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Eliminar permiso",
        operation_description="Elimina un permiso del sistema, revocando el acceso de un rol a una opción específica.",
        responses={
            204: openapi.Response("Permiso eliminado correctamente"),
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Permiso no encontrado"),
        },
        tags=["RBAC - Permisos"],
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        """Crear permiso y notificar a los usuarios afectados."""
        permiso = serializer.save()
        # Notificar a todos los usuarios con este rol
        notificar_cambios_permisos_multiples(permiso.rol)

    def perform_update(self, serializer):
        """Actualizar permiso completamente y notificar a los usuarios afectados."""
        permiso = serializer.save()
        # Notificar a todos los usuarios con este rol
        notificar_cambios_permisos_multiples(permiso.rol)

    def perform_partial_update(self, serializer):
        """Actualizar permiso parcialmente y notificar a los usuarios afectados."""
        permiso = serializer.save()
        # Notificar a todos los usuarios con este rol
        notificar_cambios_permisos_multiples(permiso.rol)

    def perform_destroy(self, instance):
        """Eliminar permiso y notificar a los usuarios afectados."""
        rol_afectado = instance.rol
        instance.delete()
        # Notificar a todos los usuarios con este rol
        notificar_cambios_permisos_multiples(rol_afectado)
