from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.sigesi.models import LineaInvestigacion, Proyecto, Semillero
from apps.sigesi.utils.aval import validar_semilleros_avalados

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

    def validate(self, data: dict) -> dict:
        """Aplica el aval institucional sobre los semilleros del proyecto.

        Resuelve los semilleros a evaluar (los enviados o, en actualización
        parcial sin envío, los ya vinculados a la instancia) y delega la
        comprobación de aval al validador centralizado.

        Args:
            data: Datos ya validados por campo (puede incluir ``semilleros``).

        Returns:
            Los ``data`` sin modificar.

        Raises:
            serializers.ValidationError: Si algún semillero no está avalado.
        """
        request = self.context.get('request')
        user = request.user if request else None

        semilleros = data.get('semilleros')
        if semilleros is None and self.instance:
            semilleros = list(self.instance.semilleros.all())
        if semilleros:
            validar_semilleros_avalados(list(semilleros), user, field_name='semilleros')

        return data

    def create(self, validated_data: dict) -> Proyecto:
        """Crea un proyecto aplicando las asignaciones automáticas de estudiante."""
        request = self.context.get('request')
        user = request.user if request else None

        # Asignaciones automáticas para Estudiantes / Líderes Estudiantiles.
        if self._es_estudiante(user):
            validated_data['estado'] = Proyecto.EstadoChoices.IDEA
            validated_data['lider'] = user

        # Los M2M se extraen para asignarlos tras crear la instancia.
        semilleros = validated_data.pop('semilleros', [])
        estudiantes = validated_data.pop('estudiantes', [])

        proyecto = Proyecto.objects.create(**validated_data)
        self._asignar_relaciones(proyecto, semilleros, estudiantes, user)

        return proyecto

    def update(self, instance: Proyecto, validated_data: dict) -> Proyecto:
        """Actualiza un proyecto bloqueando cambios de estado/líder por estudiantes."""
        request = self.context.get('request')
        user = request.user if request else None

        # Prevenir que estudiantes cambien el estado o líder.
        if self._es_estudiante(user):
            validated_data.pop('estado', None)
            validated_data.pop('lider', None)

        return super().update(instance, validated_data)

    def _es_estudiante(self, user: User) -> bool:
        """Indica si el actor es estudiante o líder estudiantil (reglas restringidas)."""
        return bool(user and user.tiene_alguno_de([
            User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL,
        ]))

    def _asignar_relaciones(
        self, proyecto: Proyecto, semilleros, estudiantes, user: User,
    ) -> None:
        """Asigna los M2M del proyecto y vincula al actor si es estudiante.

        Args:
            proyecto: Instancia ya creada sobre la que se fijan las relaciones.
            semilleros: Semilleros a asociar (lista posiblemente vacía).
            estudiantes: Estudiantes a asociar (lista posiblemente vacía).
            user: Actor de la petición; si es estudiante/líder se autovincula.
        """
        if semilleros:
            proyecto.semilleros.set(semilleros)
        if estudiantes:
            proyecto.estudiantes.set(estudiantes)
        if self._es_estudiante(user):
            proyecto.estudiantes.add(user)


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
