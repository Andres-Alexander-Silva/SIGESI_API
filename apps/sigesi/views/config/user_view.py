import openpyxl
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from apps.sigesi.models import User, Menu, ProgramaAcademico
from apps.sigesi.serializers.config.user_serializer import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    UserChangePasswordSerializer,
    MenuPerfilSerializer,
    UserBulkUploadSerializer,
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
            "**Filtrado** (`?rol=<valor>`):\n"
            "- `administrador`, `director_grupo`, `director_semillero`, `lider_estudiantil`, `estudiante`\n\n"
            "**Ordenamiento** (`?ordering=<valor>`):\n"
            "- `nombre` — apellido A→Z, nombre A→Z (por defecto)\n"
            "- `-nombre` — apellido Z→A\n"
            "- `fecha` — más antiguos primero\n"
            "- `-fecha` — más recientes primero\n\n"
            "*Otros filtros adicionales (is_active, programa_academico) se habilitarán próximamente.*"
        ),
        manual_parameters=[
            openapi.Parameter(
                name='rol',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='Filtrar usuarios por un rol específico.',
                enum=[c[0] for c in User.RolChoices.choices],
            ),
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
            "`puede_consultar`, `puede_crear`, `puede_actualizar`, `puede_eliminar`.\n\n"
            "Si se indica el query param `?rol=<valor>`, se retornan únicamente los permisos "
            "del rol especificado (debe ser un rol que posea el usuario). "
            "Si no se indica, se combinan los permisos de todos los roles del usuario (OR lógico)."
        ),
        manual_parameters=[
            openapi.Parameter(
                name='rol',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='Filtrar permisos por un rol específico del usuario.',
                enum=[c[0] for c in User.RolChoices.choices],
            ),
        ],
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
            400: openapi.Response("Rol inválido o el usuario no posee ese rol"),
            401: openapi.Response("No autenticado"),
        },
        tags=["Usuarios"],
    )
    @action(detail=False, methods=['get'], url_path='mis-permisos',
            permission_classes=[IsAuthenticated])
    def mis_permisos(self, request):
        user = request.user
        rol_param = request.query_params.get('rol', None)

        if rol_param:
            # Validar que el rol solicitado sea válido y pertenezca al usuario
            roles_validos = [c[0] for c in User.RolChoices.choices]
            if rol_param not in roles_validos:
                return Response(
                    {'message': f"El rol '{rol_param}' no es válido. Opciones: {roles_validos}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if rol_param not in user.roles:
                return Response(
                    {'message': f"El usuario no posee el rol '{rol_param}'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            roles_activos = [rol_param]
        else:
            # Sin filtro: combinar todos los roles del usuario
            roles_activos = user.roles

        menus = Menu.objects.filter(
            estado=True,
            opciones__estado=True,
            opciones__permisos__rol__in=roles_activos,
        ).distinct()

        serializer = MenuPerfilSerializer(
            menus, many=True, context={'roles': roles_activos}
        )
        menus_data = [m for m in serializer.data if m['opciones']]
        return Response({'rol': rol_param or user.roles, 'menus': menus_data})

    # --------------------------------------------------- carga masiva
    @swagger_auto_schema(
        method='post',
        operation_summary="Carga masiva de usuarios",
        operation_description=(
            "Permite a un administrador registrar múltiples usuarios a partir de un archivo Excel (.xlsx). "
            "Se requiere que la primera fila contenga los siguientes encabezados (insensibles a mayúsculas): "
            "Username, Cédula, Nombres, Apellidos, Email Institucional, Correo Personal, Teléfono, Roles, Código, Programa Académico."
        ),
        request_body=UserBulkUploadSerializer,
        responses={
            200: openapi.Response("Resumen de la carga"),
            400: openapi.Response("Datos o archivo inválido"),
            403: openapi.Response("Sin permisos"),
        },
        tags=["Usuarios"],
    )
    @action(detail=False, methods=['post'], url_path='bulk-upload',
            permission_classes=[IsAuthenticated], parser_classes=[MultiPartParser])
    def bulk_upload(self, request):
        from django.db.models import Q  # Import local to avoid cluttering top or check if it's there
        if not request.user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return Response(
                {"detail": "No tiene permisos para realizar esta acción."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = UserBulkUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        excel_file = serializer.validated_data['file']

        try:
            wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
            sheet = wb.active
        except Exception as e:
            return Response(
                {"error": f"Error al procesar el archivo Excel: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        rows = list(sheet.iter_rows(values_only=True))
        if len(rows) < 2:
            return Response(
                {"error": "El archivo debe contener al menos una fila de encabezados y una fila de datos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extraer encabezados y mapear a índices
        headers = [str(h).strip().lower() if h else '' for h in rows[0]]
        
        required_columns = {
            'username': ['username', 'usuario'],
            'cedula': ['cedula', 'cédula', 'identificacion', 'identificación'],
            'nombres': ['nombres', 'nombre'],
            'apellidos': ['apellidos', 'apellido'],
            'email': ['email institucional', 'email', 'correo institucional'],
            'correo_personal': ['correo personal', 'email personal'],
            'telefono': ['telefono', 'teléfono', 'celular'],
            'roles': ['roles', 'rol'],
            'codigo': ['codigo', 'código', 'codigo estudiantil', 'código estudiantil'],
            'programa_academico': ['programa academico', 'programa académico']
        }

        col_indices = {}
        for key, possible_names in required_columns.items():
            found = False
            for idx, header in enumerate(headers):
                if header in possible_names:
                    col_indices[key] = idx
                    found = True
                    break
            if not found and key in ['cedula', 'nombres', 'apellidos', 'email', 'correo_personal', 'roles', 'codigo']:
                return Response(
                    {"error": f"No se encontró la columna obligatoria para '{key}'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        creados = 0
        omitidos = 0
        errores = []

        cedulas_en_archivo = set()
        emails_en_archivo = set()

        valid_users_data = []

        programas_dict = {p.nombre.strip().lower(): p.id for p in ProgramaAcademico.objects.all()}

        for row_idx, row in enumerate(rows[1:], start=2):
            if not any(row):
                continue

            # Helper para obtener el valor seguro
            def get_val(key, lower=False):
                idx = col_indices.get(key)
                if idx is not None and idx < len(row) and row[idx] is not None:
                    val = str(row[idx]).strip()
                    return val.lower() if lower else val
                return ''

            cedula = get_val('cedula', lower=True)
            username = get_val('username', lower=True) or cedula
            nombres = get_val('nombres')
            apellidos = get_val('apellidos')
            email = get_val('email', lower=True)
            correo_personal = get_val('correo_personal', lower=True)
            telefono = get_val('telefono')
            roles_str = get_val('roles', lower=True)
            codigo = get_val('codigo', lower=True)
            prog_acad_str = get_val('programa_academico', lower=True)

            if not cedula or not email or not nombres or not apellidos or not correo_personal or not username:
                errores.append({"fila": row_idx, "error": "Faltan datos obligatorios (username, cédula, nombres, apellidos, email institucional o correo personal)."})
                continue

            if not email.endswith('@ufps.edu.co'):
                errores.append({"fila": row_idx, "error": f"El email {email} no pertenece al dominio @ufps.edu.co."})
                continue

            if cedula in cedulas_en_archivo or email in emails_en_archivo:
                errores.append({"fila": row_idx, "error": f"El usuario (cédula {cedula} o email {email}) está duplicado en el mismo archivo."})
                continue
            
            cedulas_en_archivo.add(cedula)
            emails_en_archivo.add(email)

            if User.objects.filter(Q(cedula=cedula) | Q(email=email) | Q(correo_personal=correo_personal)).exists():
                omitidos += 1
                continue

            roles_lista = []
            if roles_str:
                roles_split = [r.strip() for r in roles_str.split(',')]
                for r in roles_split:
                    if r in ['administrador', 'admin', 'administradora']:
                        roles_lista.append(User.RolChoices.ADMINISTRADOR)
                    elif r in ['director de grupo', 'director grupo', 'directora de grupo', 'director_grupo']:
                        roles_lista.append(User.RolChoices.DIRECTOR_GRUPO)
                    elif r in ['director de semillero', 'director semillero', 'directora de semillero', 'director_semillero']:
                        roles_lista.append(User.RolChoices.DIRECTOR_SEMILLERO)
                    elif r in ['lider estudiantil', 'líder estudiantil', 'lider', 'líder', 'lider_estudiantil']:
                        roles_lista.append(User.RolChoices.LIDER_ESTUDIANTIL)
                    elif r in ['estudiante', 'estudiantes']:
                        roles_lista.append(User.RolChoices.ESTUDIANTE)
                    else:
                        # Fallback por si lo escriben parcialmente
                        if 'admin' in r: roles_lista.append(User.RolChoices.ADMINISTRADOR)
                        elif 'grupo' in r: roles_lista.append(User.RolChoices.DIRECTOR_GRUPO)
                        elif 'semillero' in r: roles_lista.append(User.RolChoices.DIRECTOR_SEMILLERO)
                        elif 'lider' in r or 'líder' in r: roles_lista.append(User.RolChoices.LIDER_ESTUDIANTIL)
                        elif 'estudiante' in r: roles_lista.append(User.RolChoices.ESTUDIANTE)
            else:
                roles_lista.append(User.RolChoices.ESTUDIANTE)

            roles_lista = list(set(roles_lista))

            programa_academico_id = None
            if prog_acad_str:
                programa_academico_id = programas_dict.get(prog_acad_str.lower())

            valid_users_data.append({
                'username': username,
                'cedula': cedula,
                'first_name': nombres,
                'last_name': apellidos,
                'email': email,
                'correo_personal': correo_personal,
                'telefono': telefono,
                'roles': roles_lista,
                'codigo_estudiantil': codigo,
                'programa_academico_id': programa_academico_id,
            })

        with transaction.atomic():
            for user_data in valid_users_data:
                try:
                    user = User(
                        username=user_data['username'],
                        cedula=user_data['cedula'],
                        first_name=user_data['first_name'],
                        last_name=user_data['last_name'],
                        email=user_data['email'],
                        correo_personal=user_data['correo_personal'],
                        telefono=user_data['telefono'],
                        roles=user_data['roles'],
                        codigo_estudiantil=user_data['codigo_estudiantil'],
                        programa_academico_id=user_data['programa_academico_id'],
                    )
                    user.set_password(user_data['cedula'])
                    user.save()
                    creados += 1
                except Exception as e:
                    errores.append({"fila": "N/A", "error": f"Error guardando al usuario con cédula {user_data['cedula']}: {str(e)}"})

        return Response({
            "creados": creados,
            "omitidos": omitidos,
            "errores": errores
        }, status=status.HTTP_200_OK)

