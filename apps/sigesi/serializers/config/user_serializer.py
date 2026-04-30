from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.core.validators import RegexValidator
from django.db.models import Q
from apps.sigesi.models import User, Menu, Opcion, Permiso


# ---------------------------------------------------------------
# Serializers para el perfil de permisos del usuario autenticado
# ---------------------------------------------------------------

class OpcionPerfilSerializer(serializers.ModelSerializer):
    """
    Opción con los 4 permisos CRUD combinados de todos los roles del usuario.
    El front lee opcion.puede_consultar, opcion.puede_crear, etc.
    Si cualquier rol otorga el permiso, se otorga al usuario.
    """
    puede_consultar  = serializers.SerializerMethodField()
    puede_crear      = serializers.SerializerMethodField()
    puede_actualizar = serializers.SerializerMethodField()
    puede_eliminar   = serializers.SerializerMethodField()

    class Meta:
        model = Opcion
        fields = ['id', 'nombre', 'url', 'puede_consultar', 'puede_crear', 'puede_actualizar', 'puede_eliminar']

    def _permisos_combinados(self, opcion):
        """Combina permisos de todos los roles del usuario (OR lógico)."""
        roles = self.context.get('roles', [])
        cache = self.context.setdefault('_permiso_cache', {})
        key = (opcion.pk, tuple(roles))
        if key not in cache:
            permisos = Permiso.objects.filter(opcion=opcion, rol__in=roles)
            cache[key] = {
                'puede_consultar': any(p.puede_consultar for p in permisos),
                'puede_crear': any(p.puede_crear for p in permisos),
                'puede_actualizar': any(p.puede_actualizar for p in permisos),
                'puede_eliminar': any(p.puede_eliminar for p in permisos),
            }
        return cache[key]

    def get_puede_consultar(self, opcion):
        return self._permisos_combinados(opcion).get('puede_consultar', False)

    def get_puede_crear(self, opcion):
        return self._permisos_combinados(opcion).get('puede_crear', False)

    def get_puede_actualizar(self, opcion):
        return self._permisos_combinados(opcion).get('puede_actualizar', False)

    def get_puede_eliminar(self, opcion):
        return self._permisos_combinados(opcion).get('puede_eliminar', False)


class MenuPerfilSerializer(serializers.ModelSerializer):
    """Menú con sus opciones y permisos CRUD combinados por roles."""
    opciones = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = ['id', 'nombre', 'icono', 'opciones']

    def get_opciones(self, menu):
        roles = self.context.get('roles', [])
        opcion_ids = Permiso.objects.filter(
            opcion__menu=menu,
            opcion__estado=True,
            rol__in=roles,
        ).filter(
            Q(puede_consultar=True) |
            Q(puede_crear=True) |
            Q(puede_actualizar=True) |
            Q(puede_eliminar=True)
        ).values_list('opcion_id', flat=True)
        opciones = Opcion.objects.filter(id__in=opcion_ids).order_by('nombre')
        return OpcionPerfilSerializer(opciones, many=True, context=self.context).data


class UserSerializer(serializers.ModelSerializer):
    """Serializer de lectura — no expone la contraseña."""

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'correo_personal', 'is_graduated', 
            'first_name', 'last_name', 'cedula', 'telefono', 'foto', 'roles',
            'codigo_estudiantil', 'programa_academico',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear un usuario. Encripta la contraseña automáticamente."""

    email = serializers.EmailField(
        required=False,
        allow_null=True,
        validators=[
            RegexValidator(
                regex=r'^[\w\.-]+@ufps\.edu\.co$',
                message='El correo debe pertenecer al dominio @ufps.edu.co.'
            ),
            UniqueValidator(
                queryset=User.objects.all(),
                message='Ya existe un usuario registrado con este correo electrónico.'
            ),
        ]
    )
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='Mínimo 8 caracteres.',
    )
    codigo_estudiantil = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'El código estudiantil es obligatorio.',
            'blank': 'Este campo no puede quedar en blanco.'
        }
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'correo_personal', 'is_graduated',
            'password', 'first_name', 'last_name', 'cedula',
            'telefono', 'roles', 'codigo_estudiantil', 'programa_academico',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)   # encripta con PBKDF2/bcrypt según configuración
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar datos del usuario (sin cambiar contraseña)."""

    email = serializers.EmailField(
        required=False,
        allow_null=True,
        validators=[
            RegexValidator(
                regex=r'^[\w\.-]+@ufps\.edu\.co$',
                message='El correo debe pertenecer al dominio @ufps.edu.co.'
            ),
        ]
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'correo_personal', 'is_graduated',
            'first_name', 'last_name', 'cedula', 'telefono', 'foto', 'roles',
            'codigo_estudiantil', 'programa_academico', 'is_active',
        ]

    def validate_email(self, value):
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError(
                'Ya existe un usuario registrado con este correo electrónico.'
            )
        return value


class UserChangePasswordSerializer(serializers.Serializer):
    """Serializer para cambiar la contraseña de un usuario."""

    password_actual = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )
    password_nuevo = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='Mínimo 8 caracteres.',
    )
    password_confirmacion = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )

    def validate(self, data):
        if data['password_nuevo'] != data['password_confirmacion']:
            raise serializers.ValidationError(
                {'password_confirmacion': 'Las contraseñas nuevas no coinciden.'}
            )
        return data

    def validate_password_actual(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('La contraseña actual es incorrecta.')
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['password_nuevo'])
        user.save()
        return user


class UserBulkUploadSerializer(serializers.Serializer):
    """Serializer para la carga masiva de usuarios desde un archivo Excel."""
    file = serializers.FileField(
        help_text='Archivo Excel (.xlsx) con los datos de los usuarios.'
    )

    def validate_file(self, value):
        if not value.name.endswith('.xlsx'):
            raise serializers.ValidationError('El archivo debe tener extensión .xlsx.')
        return value

