from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.sigesi.models import MatriculaSemillero, Semillero
from apps.sigesi.utils.aval import validar_semilleros_avalados

User = get_user_model()

# Roles que un usuario puede tener dentro de un semillero (opción mostrada al front).
ROL_SEMILLERO_CHOICES = [
    ('estudiante', 'Estudiante'),
    ('lider_estudiantil', 'Líder Estudiantil'),
]


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
    rol_en_semillero = serializers.SerializerMethodField()

    class Meta:
        model = MatriculaSemillero
        fields = [
            'id', 'estudiante', 'estudiante_nombre', 'estudiante_codigo',
            'semillero', 'semillero_nombre', 'semestre', 'rol_en_semillero',
            'fecha_inscripcion', 'estado', 'created_at',
        ]

    def get_estudiante_nombre(self, obj):
        if obj.estudiante:
            return obj.estudiante.get_full_name()
        return None

    def get_rol_en_semillero(self, obj):
        """Líder si es el líder estudiantil actual del semillero; si no, estudiante."""
        if obj.estudiante_id and obj.estudiante_id == obj.semillero.lider_estudiantil_id:
            return 'lider_estudiantil'
        return 'estudiante'


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
    rol_en_semillero = serializers.ChoiceField(
        choices=ROL_SEMILLERO_CHOICES,
        default='estudiante',
        required=False,
        help_text='Rol del usuario dentro del semillero: estudiante o lider_estudiantil.',
    )

    class Meta:
        model = MatriculaSemillero
        fields = ['estudiante', 'semillero', 'semestre', 'rol_en_semillero']
        validators = []

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

        # --- Si el usuario es estudiante, no puede inscribir a otra persona ---
        if user.tiene_rol(User.RolChoices.ESTUDIANTE) and estudiante.id != user.id:
            raise serializers.ValidationError({
                'estudiante': 'Un estudiante solo puede inscribirse a sí mismo.'
            })

        # --- Validar que el usuario a inscribir sea estudiante o líder estudiantil ---
        if not estudiante.tiene_alguno_de([
            User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL,
        ]):
            raise serializers.ValidationError({
                'estudiante': 'Solo se puede inscribir a usuarios con rol estudiante o líder estudiantil.'
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
                and not user.tiene_rol(User.RolChoices.ADMINISTRADOR)
                and estudiante.id != user.id):
            if semillero.director_id != user.id:
                raise serializers.ValidationError({
                    'semillero': 'Solo puede inscribir estudiantes en semilleros que usted dirige.'
                })

        # --- Validar aval del semillero ---
        validar_semilleros_avalados([semillero], user, field_name='semillero')

        # --- Designar líder estudiantil: solo admin / director del semillero / director de grupo ---
        if attrs.get('rol_en_semillero') == 'lider_estudiantil':
            puede_designar = (
                user.tiene_alguno_de([
                    User.RolChoices.ADMINISTRADOR, User.RolChoices.DIRECTOR_GRUPO,
                ])
                or (user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO)
                    and semillero.director_id == user.id)
            )
            if not puede_designar:
                raise serializers.ValidationError({
                    'rol_en_semillero': (
                        'Solo un administrador, el director del semillero o un '
                        'director de grupo puede designar al líder estudiantil.'
                    )
                })

        return attrs

    def create(self, validated_data):
        rol_en_semillero = validated_data.pop('rol_en_semillero', 'estudiante')

        with transaction.atomic():
            matricula = MatriculaSemillero.objects.create(**validated_data)

            if rol_en_semillero == 'lider_estudiantil':
                semillero = matricula.semillero
                nuevo_lider = matricula.estudiante
                # El líder anterior conserva su matrícula; solo deja de ser el
                # líder del semillero (se deriva del FK). Sus roles globales no
                # se modifican (puede liderar otro semillero).
                semillero.lider_estudiantil = nuevo_lider
                semillero.save(update_fields=['lider_estudiantil', 'updated_at'])

                # El nuevo líder gana el rol global lider_estudiantil
                # (User.save() añade además 'estudiante' por el invariante).
                if not nuevo_lider.tiene_rol(User.RolChoices.LIDER_ESTUDIANTIL):
                    nuevo_lider.roles = list(nuevo_lider.roles) + [
                        User.RolChoices.LIDER_ESTUDIANTIL]
                    nuevo_lider.save(update_fields=['roles', 'updated_at'])

        return matricula
