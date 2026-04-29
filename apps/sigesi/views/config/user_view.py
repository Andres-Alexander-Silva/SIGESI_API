from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
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
from apps.sigesi.utils.ordering import MultiFieldOrderingFilter
from apps.sigesi.filters.user_filter import UserFilter



class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet CRUD para la gestión de usuarios del sistema.

    Soporta ordenamiento dinámico mediante el parámetro ?ordering:
      - ?ordering=nombre   → ordena por apellido A→Z, luego nombre A→Z
      - ?ordering=-nombre  → ordena por apellido Z→A
      - ?ordering=fecha    → ordena por fecha de creación (más antiguos primero)
      - ?ordering=-fecha   → ordena por fecha de creación (más recientes primero)

    Filtros futuros se agregan en apps/sigesi/filters/user_filter.py (UserFilter).
    """

    queryset           = User.objects.all().select_related('programa_academico')
    permission_classes = [IsAuthenticated]

    # ---- Ordenamiento y filtros ----------------------------------------
    filter_backends  = [DjangoFilterBackend, MultiFieldOrderingFilter]
    filterset_class  = UserFilter

    # Mapeo de alias legibles → campos reales del modelo
    ordering_aliases = {
        'nombre': ['last_name', 'first_name'],
        'fecha':  ['created_at'],
    }
    ordering = ['last_name', 'first_name']   # orden por defecto

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
        operation_description=(
            "Retorna la lista paginada de todos los usuarios registrados en el sistema.\n\n"
            "**Ordenamiento** (`?ordering=<valor>`):\n"
            "- `nombre` — apellido A→Z, nombre A→Z (por defecto)\n"
            "- `-nombre` — apellido Z→A\n"
            "- `fecha` — más antiguos primero\n"
            "- `-fecha` — más recientes primero\n\n"
            "*Los filtros adicionales (rol, is_active, programa_academico) se habilitarán próximamente.*"
        ),
        manual_parameters=[
            openapi.Parameter(
                name='ordering',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='Criterio de ordenamiento: `nombre`, `-nombre`, `fecha`, `-fecha`.',
                enum=['nombre', '-nombre', 'fecha', '-fecha'],
            ),
        ],
        responses={
            200: UserSerializer(many=True),
            401: openapi.Response("No autenticado"),
        },
        tags=["Usuarios"],
    )
    def list(self, request, *args, **kwargs):
        queryset   = self.filter_queryset(self.get_queryset())
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
            "Retorna los menús del usuario autenticado con sus opciones. "
            "Cada opción incluye los 4 permisos CRUD del rol: "
            "`puede_consultar`, `puede_crear`, `puede_actualizar`, `puede_eliminar`."
        ),
        responses={
            200: openapi.Response(
                description="Menús con opciones y permisos CRUD del usuario",
                examples={
                    "application/json": {
                        "rol": "director_semillero",
                        "menus": [
                            {
                                "id": 1,
                                "nombre": "Dashboard",
                                "icono": "fa-gauge",
                                "opciones": [
                                    {
                                        "id": 1,
                                        "nombre": "Dashboard",
                                        "url": "/dashboard",
                                        "puede_consultar": True,
                                        "puede_crear": False,
                                        "puede_actualizar": False,
                                        "puede_eliminar": False,
                                    }
                                ],
                            },
                            {
                                "id": 2,
                                "nombre": "Semilleros",
                                "icono": "fa-flask",
                                "opciones": [
                                    {
                                        "id": 2,
                                        "nombre": "Semilleros",
                                        "url": "/semilleros",
                                        "puede_consultar": True,
                                        "puede_crear": False,
                                        "puede_actualizar": True,
                                        "puede_eliminar": False,
                                    }
                                ],
                            },
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
        # Combinar menús accesibles por cualquiera de los roles del usuario
        menus = Menu.objects.filter(
            estado=True,
            opciones__estado=True,
            opciones__permisos__rol__in=user.roles,
        ).distinct()

        serializer = MenuPerfilSerializer(
            menus, many=True, context={'roles': user.roles}
        )
        menus_data = [m for m in serializer.data if m['opciones']]
        return Response({'roles': user.roles, 'menus': menus_data})
