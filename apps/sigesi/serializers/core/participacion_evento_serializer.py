from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from apps.sigesi.models import ParticipacionEvento, Postulacion, User
from apps.sigesi.serializers.config.user_serializer import UserSerializer
from apps.sigesi.serializers.core.evento_serializer import EventoListSerializer
from apps.sigesi.utils.alcance import participantes_en_alcance


class ParticipacionEventoListSerializer(serializers.ModelSerializer):
    """Serializador de lectura para una participación en evento.

    Embebe el evento y el participante completos (solo lectura) y expone el
    certificado, que se sube por la acción ``cargar-certificado``.
    """

    evento = EventoListSerializer(read_only=True)
    participante = UserSerializer(read_only=True)

    class Meta:
        model = ParticipacionEvento
        fields = [
            'id', 'evento', 'participante', 'postulacion', 'produccion',
            'tipo_participacion', 'certificado', 'created_at', 'updated_at',
        ]


class ParticipacionEventoCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializador de creación/actualización de una participación en evento.

    ``certificado`` se excluye a propósito: se carga por la acción dedicada
    ``POST .../cargar-certificado/``. Reglas validadas:
    - el ``participante`` debe ser estudiante o líder estudiantil;
    - salvo el administrador, el actor solo puede registrar participantes dentro
      de su alcance (estudiantes/líderes de su grupo/semillero, y el líder a sí
      mismo) — ver :func:`participantes_en_alcance`;
    - **gate de flujo**: salvo el administrador, debe existir una
      :class:`Postulacion` *aceptada* a una convocatoria de ese evento que
      incluya al participante; si se envía ``postulacion`` explícita, esta debe
      pertenecer al mismo evento, estar aceptada y contener al participante;
    - un participante no puede repetirse en el mismo evento (``unique_together``).
    No aplica el aval gate directo: el control de semillero ya ocurrió en la
    Postulación.
    """

    class Meta:
        model = ParticipacionEvento
        fields = [
            'evento', 'participante', 'postulacion', 'produccion',
            'tipo_participacion',
        ]
        validators = [
            UniqueTogetherValidator(
                queryset=ParticipacionEvento.objects.all(),
                fields=['participante', 'evento'],
                message='Este participante ya está registrado en el evento.',
            )
        ]

    def validate_participante(self, value):
        """Verifica que el participante sea estudiante o líder estudiantil."""
        if not value.tiene_alguno_de([
            User.RolChoices.ESTUDIANTE,
            User.RolChoices.LIDER_ESTUDIANTIL,
        ]):
            raise serializers.ValidationError(
                'El participante debe ser estudiante o líder estudiantil.'
            )
        return value

    def validate(self, attrs: dict) -> dict:
        """Valida una participación aplicando las reglas de negocio en orden.

        Determina el actor y, salvo que sea administrador, verifica que el
        participante esté en su alcance y que exista el respaldo de una
        postulación aceptada (gate de flujo) para ese evento.

        Args:
            attrs: Datos ya validados por campo (incluye ``evento``,
                ``participante`` y, opcionalmente, ``postulacion``).

        Returns:
            Los ``attrs`` sin modificar.

        Raises:
            serializers.ValidationError: Si alguna regla de negocio no se cumple.
        """
        request = self.context.get('request')
        user = request.user if request else None
        participante = attrs.get(
            'participante', getattr(self.instance, 'participante', None))
        evento = attrs.get('evento', getattr(self.instance, 'evento', None))
        postulacion = attrs.get(
            'postulacion', getattr(self.instance, 'postulacion', None))

        es_admin = bool(
            user and user.is_authenticated
            and user.tiene_rol(User.RolChoices.ADMINISTRADOR)
        )

        if user and user.is_authenticated and not es_admin:
            self._validar_alcance_actor(participante, user)
            self._validar_gate_postulacion(participante, evento, postulacion)

        return attrs

    def _validar_alcance_actor(self, participante, user: User) -> None:
        """El participante debe estar dentro del alcance (grupo/semillero) del actor."""
        if participante is None or not participantes_en_alcance(
                user).filter(pk=participante.pk).exists():
            raise serializers.ValidationError({
                'participante': (
                    'No puede registrar a este participante: no pertenece a '
                    'su grupo o semillero.'
                )
            })

    def _validar_gate_postulacion(
        self, participante, evento, postulacion,
    ) -> None:
        """Exige el respaldo de una postulación aceptada del evento para el participante.

        Si se envía ``postulacion`` explícita, valida que pertenezca al evento,
        esté aceptada y contenga al participante; de lo contrario, comprueba que
        exista alguna postulación aceptada del evento que lo incluya.
        """
        if postulacion is not None:
            if evento is not None and postulacion.convocatoria.evento_id != evento.id:
                raise serializers.ValidationError({
                    'postulacion': (
                        'La postulación no corresponde al evento indicado.'
                    )
                })
            if postulacion.estado != Postulacion.EstadoChoices.ACEPTADA:
                raise serializers.ValidationError({
                    'postulacion': 'La postulación indicada no está aceptada.'
                })
            if not postulacion.estudiantes.filter(
                    pk=participante.pk).exists():
                raise serializers.ValidationError({
                    'participante': (
                        'El participante no figura en la postulación indicada.'
                    )
                })
            return
        if evento is not None and not Postulacion.objects.filter(
                convocatoria__evento=evento,
                estado=Postulacion.EstadoChoices.ACEPTADA,
                estudiantes=participante,
        ).exists():
            raise serializers.ValidationError({
                'participante': (
                    'No existe una postulación aceptada que habilite la '
                    'participación de este participante en el evento.'
                )
            })
