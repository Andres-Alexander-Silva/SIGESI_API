from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from apps.sigesi.models import User, Menu
from apps.sigesi.serializers.config.user_serializer import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    UserChangePasswordSerializer,
    MenuPerfilSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet CRUD para la gestión de usuarios del sistema.
    """
    queryset = User.objects.all().order_by('last_name', 'first_name')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]

    # ------------------------------------------------------------------ list
    @swagger_auto_schema(
        operation_summary="Listar usuarios",
        operation_description="Retorna la lista de todos los usuarios registrados en el sistema.",
        responses={
            200: UserSerializer(many=True),
            401: openapi.Response("No autenticado"),
        },
        tags=["Usuarios"],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # ----------------------------------------------------------------- create
    @swagger_auto_schema(
        operation_summary="Crear usuario",
        operation_description=(
            "Registra un nuevo usuario en el sistema. "
            "La contraseña se encripta automáticamente usando `set_password` de Django (PBKDF2-SHA256). "
            "El correo debe pertenecer al dominio `@ufps.edu.co`."
        ),
        request_body=UserCreateSerializer,
        responses={
            201: UserSerializer,
            400: openapi.Response("Datos inválidos"),
        },
        tags=["Usuarios"],
    )
    def create(self, request, *args, **kwargs):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {'message': 'Usuario creado con éxito', 'data': UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )

    # --------------------------------------------------------------- retrieve
    @swagger_auto_schema(
        operation_summary="Obtener usuario",
        operation_description="Retorna el detalle de un usuario específico por su ID.",
        responses={
            200: UserSerializer,
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Usuario no encontrado"),
        },
        tags=["Usuarios"],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # ----------------------------------------------------------------- update
    @swagger_auto_schema(
        operation_summary="Actualizar usuario (completo)",
        operation_description="Actualiza todos los campos editables de un usuario. No modifica la contraseña.",
        request_body=UserUpdateSerializer,
        responses={
            200: UserSerializer,
            400: openapi.Response("Datos inválidos"),
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Usuario no encontrado"),
        },
        tags=["Usuarios"],
    )
    def update(self, request, *args, **kwargs):
        kwargs['partial'] = False
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)

    # ---------------------------------------------------------- partial_update
    @swagger_auto_schema(
        operation_summary="Actualizar usuario (parcial)",
        operation_description="Actualiza uno o más campos de un usuario sin necesidad de enviar todos los campos. No modifica la contraseña.",
        request_body=UserUpdateSerializer,
        responses={
            200: UserSerializer,
            400: openapi.Response("Datos inválidos"),
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Usuario no encontrado"),
        },
        tags=["Usuarios"],
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)

    # ---------------------------------------------------------------- destroy
    @swagger_auto_schema(
        operation_summary="Eliminar usuario",
        operation_description="Elimina un usuario del sistema de forma permanente.",
        responses={
            204: openapi.Response("Usuario eliminado correctamente"),
            401: openapi.Response("No autenticado"),
            404: openapi.Response("Usuario no encontrado"),
        },
        tags=["Usuarios"],
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --------------------------------------------------- cambiar contraseña
    @swagger_auto_schema(
        method='post',
        operation_summary="Cambiar contraseña",
        operation_description=(
            "Permite al usuario autenticado cambiar su propia contraseña. "
            "Se requiere la contraseña actual para confirmar la identidad. "
            "La nueva contraseña se encripta automáticamente."
        ),
        request_body=UserChangePasswordSerializer,
        responses={
            200: openapi.Response("Contraseña actualizada correctamente"),
            400: openapi.Response("Datos inválidos o contraseña actual incorrecta"),
            401: openapi.Response("No autenticado"),
        },
        tags=["Usuarios"],
    )
    @action(detail=False, methods=['post'], url_path='cambiar-password',
            permission_classes=[IsAuthenticated])
    def cambiar_password(self, request):
        serializer = UserChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Contraseña actualizada correctamente.'})

    # --------------------------------------------------- mis permisos
    @swagger_auto_schema(
        method='get',
        operation_summary="Mis menús, opciones y permisos",
        operation_description=(
            "Retorna todos los menús accesibles para el usuario autenticado, "
            "junto con sus opciones y el permiso asociado según su rol. "
            "Solo se incluyen menús y opciones activos con `permitido=true`."
        ),
        responses={
            200: openapi.Response(
                description="Estructura de menús con opciones y permisos del usuario",
                examples={
                    "application/json": {
                        "rol": "estudiante",
                        "menus": [
                            {
                                "id": 1,
                                "nombre": "Semilleros",
                                "icono": "fa-flask",
                                "orden": 1,
                                "url": "/semilleros",
                                "menu_padre": None,
                                "opciones": [
                                    {
                                        "id": 3,
                                        "nombre": "Ver semilleros",
                                        "codigo": "semilleros.ver",
                                        "descripcion": "",
                                        "accion": "ver",
                                        "permiso": {"id": 5, "permitido": True},
                                    }
                                ],
                            }
                        ],
                    }
                },
            ),
            401: openapi.Response("No autenticado"),
        },
        tags=["Usuarios"],
    )
    @action(detail=False, methods=['get'], url_path='mis-permisos',
            permission_classes=[IsAuthenticated])
    def mis_permisos(self, request):
        user = request.user
        menus = Menu.objects.filter(
            opciones__permisos__rol=user.rol,
            opciones__permisos__permitido=True,
            opciones__is_active=True,
            is_active=True,
        ).distinct().order_by('orden')

        serializer = MenuPerfilSerializer(
            menus, many=True, context={'rol': user.rol}
        )
        return Response({'rol': user.rol, 'menus': serializer.data})
