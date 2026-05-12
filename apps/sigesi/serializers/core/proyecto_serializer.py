from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model
from apps.sigesi.models import Proyecto, Semillero, LineaInvestigacion

User = get_user_model()

class ProyectoListSerializer(serializers.ModelSerializer):
    """
    Serializer para listar y consultar detalles de Proyectos.
    """
    director_nombre = serializers.SerializerMethodField()
    lider_nombre = serializers.SerializerMethodField()
    linea_investigacion_nombre = serializers.CharField(source='linea_investigacion.nombre', read_only=True)
    semilleros_nombres = serializers.SerializerMethodField()
    estudiantes_nombres = serializers.SerializerMethodField()

    class Meta:
        model = Proyecto
        fields = [
            'id', 'titulo', 'codigo', 'descripcion', 'objetivo_general', 'objetivos_especificos',
            'semilleros', 'semilleros_nombres', 'linea_investigacion', 'linea_investigacion_nombre',
            'director', 'director_nombre', 'lider', 'lider_nombre', 'estudiantes', 'estudiantes_nombres',
            'estado', 'fecha_inicio', 'fecha_fin_estimada', 'fecha_cierre', 'is_active',
            'created_at', 'updated_at'
        ]

    def get_director_nombre(self, obj):
        return obj.director.get_full_name() if obj.director else None

    def get_lider_nombre(self, obj):
        return obj.lider.get_full_name() if obj.lider else None

    def get_semilleros_nombres(self, obj):
        return [sem.nombre for sem in obj.semilleros.all()]

    def get_estudiantes_nombres(self, obj):
        return [est.get_full_name() for est in obj.estudiantes.all()]


class ProyectoCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para creación y actualización de Proyectos.
    """
    codigo = serializers.CharField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=Proyecto.objects.all(),
                message='Ya existe un proyecto registrado con este código.'
            )
        ]
    )

    class Meta:
        model = Proyecto
        fields = [
            'titulo', 'codigo', 'descripcion', 'objetivo_general', 'objetivos_especificos',
            'semilleros', 'linea_investigacion', 'director', 'lider', 'estudiantes',
            'estado', 'fecha_inicio', 'fecha_fin_estimada', 'fecha_cierre', 'is_active'
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None

        # Asignaciones automáticas para Estudiantes
        if user and user.tiene_alguno_de([User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL]):
            validated_data['estado'] = Proyecto.EstadoChoices.IDEA
            validated_data['lider'] = user
            
            # Asegurar que el estudiante se incluya en los estudiantes vinculados si es necesario
            # Como es M2M se añade después de guardar la instancia
            
        semilleros = validated_data.pop('semilleros', [])
        estudiantes = validated_data.pop('estudiantes', [])
        
        proyecto = Proyecto.objects.create(**validated_data)
        
        if semilleros:
            proyecto.semilleros.set(semilleros)
        if estudiantes:
            proyecto.estudiantes.set(estudiantes)
            
        if user and user.tiene_alguno_de([User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL]):
            proyecto.estudiantes.add(user)

        return proyecto

    def update(self, instance, validated_data):
        request = self.context.get('request')
        user = request.user if request else None

        # Prevenir que estudiantes cambien el estado o líder
        if user and user.tiene_alguno_de([User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL]):
            validated_data.pop('estado', None)
            validated_data.pop('lider', None)

        return super().update(instance, validated_data)


class ProyectoChangeStateSerializer(serializers.ModelSerializer):
    """
    Serializer exclusivo para que directores y admins cambien el estado del proyecto.
    """
    class Meta:
        model = Proyecto
        fields = ['estado']

    def validate_estado(self, value):
        request = self.context.get('request')
        user = request.user if request else None
        
        if user and user.tiene_alguno_de([User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL]):
            raise serializers.ValidationError("Los estudiantes no tienen permisos para cambiar el estado del proyecto.")
            
        return value
