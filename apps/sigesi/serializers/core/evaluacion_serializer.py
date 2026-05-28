from decimal import Decimal

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.sigesi.models import Evaluacion, User
from apps.sigesi.serializers.core.competencia_investigativa_serializer import (
    CompetenciaInvestigativaListSerializer,
)
from apps.sigesi.utils.aval import validar_semilleros_avalados


class EvaluacionListSerializer(serializers.ModelSerializer):
    """Serializador de lectura para una Evaluación de competencias.

    Embebe la competencia completa (que a su vez trae su semillero) y expone los
    nombres del estudiante evaluado y del evaluador, además de los campos de
    calificación (``puntaje``, ``observaciones``, ``nivel_alcanzado``) que se
    fijan mediante la acción ``calificar``.
    """

    competencia = CompetenciaInvestigativaListSerializer(read_only=True)
    estudiante_nombre = serializers.SerializerMethodField()
    evaluador_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Evaluacion
        fields = [
            'id', 'estudiante', 'estudiante_nombre', 'evaluador',
            'evaluador_nombre', 'competencia', 'tipo', 'nivel_alcanzado',
            'puntaje', 'observaciones', 'semestre', 'fecha',
            'created_at', 'updated_at',
        ]

    def get_estudiante_nombre(self, obj):
        """Nombre completo del estudiante evaluado, o ``None``."""
        return obj.estudiante.get_full_name() if obj.estudiante else None

    def get_evaluador_nombre(self, obj):
        """Nombre completo del evaluador, o ``None`` si aún no se asignó."""
        return obj.evaluador.get_full_name() if obj.evaluador else None


class EvaluacionCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializador de creación/actualización de una Evaluación.

    Solo registra el encabezado de la evaluación; los campos de calificación
    (``puntaje``, ``observaciones``, ``nivel_alcanzado``) se excluyen a propósito
    y se fijan después mediante la acción ``calificar``. Reglas:

    - Si ``tipo`` es ``autoevaluacion`` el evaluador se fuerza al propio
      estudiante (se ignora cualquier valor enviado).
    - Si ``tipo`` es ``heteroevaluacion`` el ``evaluador`` es obligatorio en el
      cuerpo de la petición.
    - Aval gate: un usuario no administrador no puede crear ni actualizar
      evaluaciones atadas a un semillero (vía ``competencia.semillero``) cuyo
      aval no esté aprobado. El administrador omite la restricción.
    """

    class Meta:
        model = Evaluacion
        fields = ['estudiante', 'evaluador', 'competencia', 'tipo', 'semestre']
        extra_kwargs = {'evaluador': {'required': False}}

    def validate(self, data):
        """Aplica las reglas de evaluador por tipo y el aval gate del semillero."""
        request = self.context.get('request')
        user = request.user if request else None

        tipo = data.get('tipo') or (self.instance.tipo if self.instance else None)
        estudiante = data.get('estudiante') or (
            self.instance.estudiante if self.instance else None
        )

        if tipo == Evaluacion.TipoChoices.AUTOEVALUACION:
            # En autoevaluación el evaluador es siempre el propio estudiante.
            data['evaluador'] = estudiante
        elif tipo == Evaluacion.TipoChoices.HETEROEVALUACION:
            evaluador = data.get('evaluador') or (
                self.instance.evaluador if self.instance else None
            )
            if evaluador is None:
                raise serializers.ValidationError({
                    'evaluador': 'El evaluador es obligatorio para una heteroevaluación.'
                })

        competencia = data.get('competencia') or (
            self.instance.competencia if self.instance else None
        )
        if competencia is not None:
            # El Director de Semillero solo puede registrar evaluaciones de su
            # propio semillero (en create no corre has_object_permission). El
            # administrador omite esta restricción.
            if (user and not user.tiene_rol(User.RolChoices.ADMINISTRADOR)
                    and competencia.semillero.director_id != user.id):
                raise PermissionDenied(
                    'No puede registrar evaluaciones en un semillero que no dirige.'
                )

            validar_semilleros_avalados(
                [competencia.semillero], user, field_name='competencia'
            )

        return data


class EvaluacionCalificarSerializer(serializers.ModelSerializer):
    """Serializador de la acción ``calificar``: fija el resultado de la evaluación.

    Solo permite escribir ``puntaje``, ``observaciones`` y ``nivel_alcanzado``.
    El puntaje, si se envía, debe estar entre 0.0 y 5.0.
    """

    class Meta:
        model = Evaluacion
        fields = ['puntaje', 'observaciones', 'nivel_alcanzado']
        extra_kwargs = {
            'puntaje': {'required': True},
            'nivel_alcanzado': {'required': True},
        }

    def validate_puntaje(self, value):
        """Valida que el puntaje esté en el rango permitido (0.0 a 5.0)."""
        if value is not None and (value < Decimal('0.0') or value > Decimal('5.0')):
            raise serializers.ValidationError('El puntaje debe estar entre 0.0 y 5.0.')
        return value
