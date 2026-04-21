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
    Opción con los 4 permisos CRUD del rol aplanados directamente.
    El front lee opcion.puede_consultar, opcion.puede_crear, etc.
    """
    puede_consultar  = serializers.SerializerMethodField()
    puede_crear      = serializers.SerializerMethodField()
    puede_actualizar = serializers.SerializerMethodField()
    puede_eliminar   = serializers.SerializerMethodField()

    class Meta:
        model = Opcion
        fields = ['id', 'nombre', 'url', 'puede_consultar', 'puede_crear', 'puede_actualizar', 'puede_eliminar']

    def _permiso(self, opcion):
        rol = self.context.get('rol')
        # Cacheado en el contexto para no repetir queries por campo
        cache = self.context.setdefault('_permiso_cache', {})
        key = (opcion.pk, rol)
        if key not in cache:
            cache[key] = Permiso.objects.filter(opcion=opcion, rol=rol).first()
        return cache[key]

    def get_puede_consultar(self, opcion):
        p = self._permiso(opcion)
        return p.puede_consultar if p else False

    def get_puede_crear(self, opcion):
        p = self._permiso(opcion)
        return p.puede_crear if p else False

    def get_puede_actualizar(self, opcion):
        p = self._permiso(opcion)
        return p.puede_actualizar if p else False

    def get_puede_eliminar(self, opcion):
        p = self._permiso(opcion)
        return p.puede_eliminar if p else False


class MenuPerfilSerializer(serializers.ModelSerializer):
    """Menú con sus opciones y permisos CRUD por rol."""
    opciones = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = ['id', 'nombre', 'icono', 'opciones']

    def get_opciones(self, menu):
        rol = self.context.get('rol')
        opcion_ids = Permiso.objects.filter(
            opcion__menu=menu,
            opcion__estado=True,
            rol=rol,
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
            'first_name', 'last_name', 'cedula', 'telefono', 'foto', 'rol',
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

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'correo_personal', 'is_graduated',
            'password', 'first_name', 'last_name', 'cedula',
            'telefono', 'rol', 'codigo_estudiantil', 'programa_academico',
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
            'first_name', 'last_name', 'cedula', 'telefono', 'foto', 'rol',
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
