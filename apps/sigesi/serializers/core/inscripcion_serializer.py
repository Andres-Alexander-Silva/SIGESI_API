from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.sigesi.models import MatriculaSemillero, Semillero
from apps.sigesi.utils.aval import validar_semilleros_avalados
from apps.sigesi.utils.alcance import semilleros_en_alcance

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

    def validate(self, attrs: dict) -> dict:
        """Valida una inscripción aplicando todas las reglas de negocio en orden.

        Resuelve el estudiante (autoinscripción), verifica el permiso del actor,
        el rol del inscrito, el estado y el alcance del semillero, los duplicados,
        el aval institucional y la designación de líder estudiantil.

        Args:
            attrs: Datos ya validados por campo (incluye ``semillero``,
                ``semestre`` y, opcionalmente, ``estudiante``/``rol_en_semillero``).

        Returns:
            Los ``attrs`` con ``estudiante`` resuelto.

        Raises:
            serializers.ValidationError: Si alguna regla de negocio no se cumple.
        """
        user = self.context['request'].user
        semillero = attrs['semillero']

        estudiante = self._resolver_estudiante(attrs, user)
        self._validar_actor_puede_inscribir(estudiante, user)
        self._validar_rol_inscrito(estudiante)
        self._validar_semillero_activo(semillero)
        self._validar_no_duplicado(estudiante, semillero, attrs['semestre'])
        self._validar_alcance(estudiante, semillero, user)
        validar_semilleros_avalados([semillero], user, field_name='semillero')
        self._validar_designacion_lider(
            attrs.get('rol_en_semillero'), semillero, user)

        return attrs

    def _resolver_estudiante(self, attrs: dict, user: User) -> User:
        """Devuelve el estudiante a inscribir, autoasignando al actor si es estudiante."""
        estudiante = attrs.get('estudiante')
        if estudiante:
            return estudiante
        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            attrs['estudiante'] = user
            return user
        raise serializers.ValidationError({
            'estudiante': 'Debe indicar el estudiante a inscribir.'
        })

    def _validar_actor_puede_inscribir(self, estudiante: User, user: User) -> None:
        """Solo un gestor puede inscribir a alguien distinto de sí mismo.

        Un usuario que solo es estudiante —aunque por el invariante un líder
        también lleve el rol estudiante— únicamente puede autoinscribirse.
        """
        if estudiante.id == user.id:
            return
        es_gestor = user.tiene_alguno_de([
            User.RolChoices.ADMINISTRADOR,
            User.RolChoices.DIRECTOR_GRUPO,
            User.RolChoices.DIRECTOR_SEMILLERO,
            User.RolChoices.LIDER_ESTUDIANTIL,
        ])
        if not es_gestor:
            raise serializers.ValidationError({
                'estudiante': 'Un estudiante solo puede inscribirse a sí mismo.'
            })

    def _validar_rol_inscrito(self, estudiante: User) -> None:
        """El usuario a inscribir debe tener rol estudiante o líder estudiantil."""
        if not estudiante.tiene_alguno_de([
            User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL,
        ]):
            raise serializers.ValidationError({
                'estudiante': 'Solo se puede inscribir a usuarios con rol estudiante o líder estudiantil.'
            })

    def _validar_semillero_activo(self, semillero: Semillero) -> None:
        """El semillero destino debe estar activo."""
        if not semillero.is_active:
            raise serializers.ValidationError({
                'semillero': 'El semillero seleccionado no se encuentra activo.'
            })

    def _validar_no_duplicado(
        self, estudiante: User, semillero: Semillero, semestre: str,
    ) -> None:
        """No puede existir ya una matrícula del estudiante en ese semillero/semestre."""
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

    def _validar_alcance(
        self, estudiante: User, semillero: Semillero, user: User,
    ) -> None:
        """Al inscribir a otra persona, el semillero debe estar en el alcance del actor.

        El estudiante se autoinscribe a cualquier semillero (no entra aquí) y el
        administrador no tiene tope; el resto de gestores solo inscriben a otros
        en los semilleros de su alcance.
        """
        if estudiante.id == user.id or user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return
        if not semilleros_en_alcance(user).filter(pk=semillero.pk).exists():
            raise serializers.ValidationError({
                'semillero': 'Solo puede inscribir estudiantes en semilleros de su alcance.'
            })

    def _validar_designacion_lider(
        self, rol_en_semillero, semillero: Semillero, user: User,
    ) -> None:
        """Solo admin, director de grupo o el director del semillero designan líder."""
        if rol_en_semillero != 'lider_estudiantil':
            return
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

    def create(self, validated_data: dict) -> MatriculaSemillero:
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
