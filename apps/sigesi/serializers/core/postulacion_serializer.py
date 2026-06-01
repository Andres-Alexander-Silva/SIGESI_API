from rest_framework import serializers

from apps.sigesi.models import Postulacion, Convocatoria, User
from apps.sigesi.serializers.config.user_serializer import UserSerializer
from apps.sigesi.serializers.core.convocatoria_serializer import (
    ConvocatoriaListSerializer,
)
from apps.sigesi.serializers.core.semillero_serializer import (
    SemilleroListSerializer,
)
from apps.sigesi.utils.aval import validar_semilleros_avalados


class PostulacionListSerializer(serializers.ModelSerializer):
    """Serializador de lectura para una postulación de un semillero a una convocatoria.

    Embebe la convocatoria, el semillero y los estudiantes postulados completos
    (solo lectura) y expone el estado de resolución (``estado``,
    ``aprobado_por``, ``fecha_resolucion``).
    """

    convocatoria = ConvocatoriaListSerializer(read_only=True)
    semillero = SemilleroListSerializer(read_only=True)
    estudiantes = UserSerializer(many=True, read_only=True)
    aprobado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Postulacion
        fields = [
            'id', 'convocatoria', 'semillero', 'estudiantes', 'proyecto',
            'estado', 'observaciones', 'resultado', 'aprobado_por',
            'aprobado_por_nombre', 'fecha_resolucion', 'fecha_postulacion',
            'created_at', 'updated_at',
        ]

    def get_aprobado_por_nombre(self, obj):
        """Nombre completo de quien resolvió la postulación, o ``None``."""
        return obj.aprobado_por.get_full_name() if obj.aprobado_por else None


class PostulacionCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializador de creación/actualización de una postulación.

    El ``estado`` y los campos de resolución (``aprobado_por``,
    ``fecha_resolucion``, ``resultado``) se excluyen a propósito: se gestionan
    por las acciones ``aprobar``/``rechazar``. Reglas validadas:
    - el ``semillero`` debe tener aval aprobado (salvo administrador);
    - salvo el administrador, el actor solo puede postular su **propio**
      semillero (Director de Semillero);
    - todos los ``estudiantes`` deben estar matriculados en ese semillero y ser
      estudiante o líder estudiantil;
    - solo puede postularse a convocatorias en estado ``abierta`` (en creación).
    """

    class Meta:
        model = Postulacion
        fields = [
            'convocatoria', 'semillero', 'estudiantes', 'proyecto',
            'observaciones',
        ]

    def _semillero_actual(self, data):
        """Resuelve el semillero objetivo desde los datos o la instancia."""
        return data.get('semillero', getattr(self.instance, 'semillero', None))

    def validate(self, data):
        """Aplica aval gate, propiedad del semillero, matrícula y estado de la convocatoria."""
        request = self.context.get('request')
        user = request.user if request else None
        es_admin = bool(
            user and user.is_authenticated
            and user.tiene_rol(User.RolChoices.ADMINISTRADOR)
        )

        semillero = self._semillero_actual(data)

        # 1. Aval gate: el semillero debe estar aprobado (el admin lo omite).
        if semillero is not None:
            validar_semilleros_avalados([semillero], user, field_name='semillero')

        # 2. El Director de Semillero solo puede postular su propio semillero.
        if not es_admin and semillero is not None:
            if semillero.director_id != getattr(user, 'id', None):
                raise serializers.ValidationError({
                    'semillero': (
                        'Solo puede postular semilleros que usted dirige.'
                    )
                })

        # 3. Todos los estudiantes postulados deben estar matriculados en el
        #    semillero y ser estudiante o líder estudiantil.
        estudiantes = data.get('estudiantes')
        if estudiantes is None and self.instance:
            estudiantes = list(self.instance.estudiantes.all())
        if estudiantes and semillero is not None:
            for est in estudiantes:
                if not est.tiene_alguno_de([
                    User.RolChoices.ESTUDIANTE,
                    User.RolChoices.LIDER_ESTUDIANTIL,
                ]):
                    raise serializers.ValidationError({
                        'estudiantes': (
                            f'{est.get_full_name()} no es estudiante ni líder '
                            'estudiantil.'
                        )
                    })
                if not semillero.matriculas.filter(estudiante=est).exists():
                    raise serializers.ValidationError({
                        'estudiantes': (
                            f'{est.get_full_name()} no está matriculado en el '
                            'semillero postulante.'
                        )
                    })

        # 4. En creación, la convocatoria debe estar abierta.
        if self.instance is None:
            convocatoria = data.get('convocatoria')
            if convocatoria and convocatoria.estado != Convocatoria.EstadoChoices.ABIERTA:
                raise serializers.ValidationError({
                    'convocatoria': (
                        'Solo puede postularse a convocatorias en estado '
                        '"abierta".'
                    )
                })

        return data
