from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model
from apps.sigesi.models import Semillero, GrupoInvestigacion

User = get_user_model()

class SemilleroListSerializer(serializers.ModelSerializer):
    """
    Serializer para listar y consultar el detalle de Semilleros.
    Incluye información de solo lectura para campos relacionados, mejorando la respuesta.
    """
    grupo_investigacion_nombre = serializers.CharField(source='grupo_investigacion.nombre', read_only=True)
    director_nombre = serializers.SerializerMethodField()
    lider_estudiantil_nombre = serializers.SerializerMethodField()
    lineas_investigacion_nombres = serializers.SerializerMethodField()

    class Meta:
        model = Semillero
        fields = [
            'id', 'nombre', 'codigo', 'objetivo', 'mision', 'vision',
            'fecha_creacion', 'grupo_investigacion', 'grupo_investigacion_nombre',
            'director', 'director_nombre', 'lider_estudiantil', 'lider_estudiantil_nombre',
            'lineas_investigacion', 'lineas_investigacion_nombres', 'logo',
            'is_active', 'created_at', 'updated_at'
        ]

    def get_director_nombre(self, obj):
        if obj.director:
            return f"{obj.director.get_full_name()}"
        return None

    def get_lider_estudiantil_nombre(self, obj):
        if obj.lider_estudiantil:
            return f"{obj.lider_estudiantil.get_full_name()}"
        return None
        
    def get_lineas_investigacion_nombres(self, obj):
        return [linea.nombre for linea in obj.lineas_investigacion.all()]


class SemilleroCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para creación y actualización de Semilleros.
    Aplica validaciones de negocio básicas.
    """
    codigo = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'El código del semillero es obligatorio.',
            'blank': 'El código no puede estar vacío.'
        },
        validators=[
            UniqueValidator(
                queryset=Semillero.objects.all(),
                message='Ya existe un semillero registrado con este código.'
            )
        ]
    )
    grupo_investigacion = serializers.PrimaryKeyRelatedField(
        queryset=GrupoInvestigacion.objects.all(),
        required=True,
        error_messages={
            'required': 'Debe asociar el semillero a un grupo de investigación.',
            'null': 'El grupo de investigación no puede ser nulo.',
            'does_not_exist': 'El grupo de investigación seleccionado no existe.'
        }
    )
    director = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=True,
        error_messages={
            'required': 'Es obligatorio asignar un director al semillero.',
            'null': 'El director no puede ser nulo.',
            'does_not_exist': 'El usuario seleccionado como director no existe.'
        }
    )

    class Meta:
        model = Semillero
        fields = [
            'nombre', 'codigo', 'objetivo', 'mision', 'vision',
            'fecha_creacion', 'grupo_investigacion', 'director',
            'lider_estudiantil', 'lineas_investigacion', 'logo', 'is_active'
        ]
        
    def validate_grupo_investigacion(self, value):
        """Valida que el grupo de investigación asociado exista y esté activo"""
        if not value:
            raise serializers.ValidationError("Debe proporcionar un grupo de investigación válido.")
        if not value.is_active:
            raise serializers.ValidationError("El grupo de investigación seleccionado no está activo.")
        return value
