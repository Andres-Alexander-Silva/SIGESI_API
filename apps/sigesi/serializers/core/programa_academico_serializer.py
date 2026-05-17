from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from apps.sigesi.models import ProgramaAcademico


class ProgramaAcademicoSerializer(serializers.ModelSerializer):
    """Serializer de lectura y detalle para ProgramaAcademico."""

    class Meta:
        model = ProgramaAcademico
        fields = ['id', 'nombre', 'codigo', 'facultad',
                  'is_active', 'created_at', 'updated_at']


class ProgramaAcademicoCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para crear y actualizar ProgramaAcademico."""

    codigo = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'El código del programa académico es obligatorio.',
            'blank': 'El código no puede estar vacío.',
        },
        validators=[
            UniqueValidator(
                queryset=ProgramaAcademico.objects.all(),
                message='Ya existe un programa académico registrado con este código.'
            )
        ]
    )

    class Meta:
        model = ProgramaAcademico
        fields = ['nombre', 'codigo', 'facultad', 'is_active']
