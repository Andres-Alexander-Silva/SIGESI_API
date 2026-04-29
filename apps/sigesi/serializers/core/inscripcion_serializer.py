from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.sigesi.models import MatriculaSemillero, Semillero

User = get_user_model()


class InscripcionListSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para inscripciones de semillero.
    Incluye campos derivados para evitar consultas adicionales en el frontend.
    """
    estudiante_nombre = serializers.SerializerMethodField()
    estudiante_codigo = serializers.CharField(
        source='estudiante.codigo_estudiantil', read_only=True)
    semillero_nombre = serializers.CharField(
        source='semillero.nombre', read_only=True)

    class Meta:
        model = MatriculaSemillero
        fields = [
            'id', 'estudiante', 'estudiante_nombre', 'estudiante_codigo',
            'semillero', 'semillero_nombre', 'semestre',
            'fecha_inscripcion', 'estado', 'created_at',
        ]

    def get_estudiante_nombre(self, obj):
        if obj.estudiante:
            return obj.estudiante.get_full_name()
        return None


class InscripcionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear inscripciones.
    - Si el usuario es estudiante y no envía 'estudiante', se auto-asigna.
    - Valida duplicados, semillero activo, rol estudiante y alcance del director.
    """
    estudiante = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        error_messages={
            'does_not_exist': 'El estudiante seleccionado no existe.',
        }
    )
    semillero = serializers.PrimaryKeyRelatedField(
        queryset=Semillero.objects.all(),
        required=True,
        error_messages={
            'required': 'Debe seleccionar un semillero.',
            'null': 'El semillero no puede ser nulo.',
            'does_not_exist': 'El semillero seleccionado no existe.',
        }
    )
    semestre = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'Debe indicar el semestre (ej: 2025-1).',
            'blank': 'El semestre no puede estar vacío.',
        }
    )

    class Meta:
        model = MatriculaSemillero
        fields = ['estudiante', 'semillero', 'semestre']

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user

        # --- Resolver estudiante ---
        estudiante = attrs.get('estudiante')

        if not estudiante:
            # Auto-inscripción: el usuario actual es el estudiante
            if user.tiene_rol(User.RolChoices.ESTUDIANTE):
                attrs['estudiante'] = user
                estudiante = user
            else:
                raise serializers.ValidationError({
                    'estudiante': 'Debe indicar el estudiante a inscribir.'
                })

        # --- Validar que el usuario a inscribir tenga rol estudiante ---
        if not estudiante.tiene_rol(User.RolChoices.ESTUDIANTE):
            raise serializers.ValidationError({
                'estudiante': 'El usuario seleccionado no tiene el rol de estudiante.'
            })

        # --- Validar semillero activo ---
        semillero = attrs['semillero']
        if not semillero.is_active:
            raise serializers.ValidationError({
                'semillero': 'El semillero seleccionado no se encuentra activo.'
            })

        # --- Validar duplicado ---
        semestre = attrs['semestre']
        if MatriculaSemillero.objects.filter(
            estudiante=estudiante,
            semillero=semillero,
            semestre=semestre,
        ).exists():
            raise serializers.ValidationError({
                'non_field_errors': [
                    f'El estudiante ya se encuentra inscrito en el semillero '
                    f'"{semillero.nombre}" para el semestre {semestre}.'
                ]
            })

        # --- Validar alcance del Director de Semillero ---
        if (user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO)
                and not user.tiene_rol(User.RolChoices.ADMINISTRADOR)):
            if semillero.director != user:
                raise serializers.ValidationError({
                    'semillero': 'Solo puede inscribir estudiantes en semilleros que usted dirige.'
                })

        return attrs
