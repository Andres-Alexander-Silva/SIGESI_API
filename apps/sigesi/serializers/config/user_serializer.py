from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.core.validators import RegexValidator
from apps.sigesi.models import User, Menu, Opcion, Permiso


# ---------------------------------------------------------------
# Serializers para el perfil de permisos del usuario autenticado
# ---------------------------------------------------------------

class PermisoPerfilSerializer(serializers.ModelSerializer):
    """Permiso asociado a una opción, visto desde el perfil del usuario."""
    class Meta:
        model = Permiso
        fields = ['id', 'permitido']


class OpcionPerfilSerializer(serializers.ModelSerializer):
    """Opción con su permiso para el rol del usuario autenticado."""
    permiso = serializers.SerializerMethodField()

    class Meta:
        model = Opcion
        fields = ['id', 'nombre', 'codigo', 'descripcion', 'accion', 'permiso']

    def get_permiso(self, opcion):
        rol = self.context.get('rol')
        permiso = Permiso.objects.filter(opcion=opcion, rol=rol).first()
        if permiso:
            return PermisoPerfilSerializer(permiso).data
        return None


class MenuPerfilSerializer(serializers.ModelSerializer):
    """Menú con sus opciones y permisos para el rol del usuario autenticado."""
    opciones = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = ['id', 'nombre', 'icono', 'orden', 'url', 'menu_padre', 'opciones']

    def get_opciones(self, menu):
        rol = self.context.get('rol')
        opciones = Opcion.objects.filter(
            menu=menu,
            permisos__rol=rol,
            permisos__permitido=True,
            is_active=True,
        ).distinct()
        return OpcionPerfilSerializer(opciones, many=True, context=self.context).data


class UserSerializer(serializers.ModelSerializer):
    """Serializer de lectura — no expone la contraseña."""

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'cedula', 'telefono', 'foto', 'rol',
            'codigo_estudiantil', 'programa_academico',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear un usuario. Encripta la contraseña automáticamente."""

    email = serializers.EmailField(
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
            'id', 'username', 'email', 'password',
            'first_name', 'last_name', 'cedula',
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
            'username', 'email', 'first_name', 'last_name',
            'cedula', 'telefono', 'foto', 'rol',
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
