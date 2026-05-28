from rest_framework import serializers

from apps.sigesi.models import CompetenciaInvestigativa
from apps.sigesi.serializers.core.semillero_serializer import SemilleroListSerializer
from apps.sigesi.utils.aval import validar_semilleros_avalados


class CompetenciaInvestigativaListSerializer(serializers.ModelSerializer):
    """Serializador para listar y ver el detalle de una CompetenciaInvestigativa.

    Embebe la información completa del semillero asociado (solo lectura) en el
    campo ``semillero``, de modo que las respuestas de lectura traen el objeto
    del semillero y no únicamente su id.
    """

    semillero = SemilleroListSerializer(read_only=True)

    class Meta:
        model = CompetenciaInvestigativa
        fields = [
            'id', 'semillero', 'nombre', 'descripcion', 'nivel',
            'indicadores', 'is_active', 'created_at', 'updated_at',
        ]


class CompetenciaInvestigativaCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializador para crear y actualizar una CompetenciaInvestigativa.

    Aplica el aval gate del semillero: un usuario no administrador no puede
    crear ni actualizar competencias atadas a un semillero cuyo aval no esté
    aprobado. El administrador omite la restricción automáticamente.
    """

    class Meta:
        model = CompetenciaInvestigativa
        fields = [
            'semillero', 'nombre', 'descripcion', 'nivel',
            'indicadores', 'is_active',
        ]

    def validate(self, data):
        """Bloquea escrituras si el semillero asociado no tiene aval aprobado."""
        request = self.context.get('request')
        user = request.user if request else None

        semillero = data.get('semillero') or (
            self.instance.semillero if self.instance else None
        )
        if semillero is not None:
            validar_semilleros_avalados([semillero], user, field_name='semillero')

        return data
