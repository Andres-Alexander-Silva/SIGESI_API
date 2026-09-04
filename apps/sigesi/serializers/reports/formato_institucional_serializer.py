from rest_framework import serializers

from apps.sigesi.models import FormatoInstitucional
from apps.sigesi.utils.download import validate_upload_file


class FormatoInstitucionalSerializer(serializers.ModelSerializer):
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)
    tipo_vinculacion_display = serializers.CharField(
        source='get_tipo_vinculacion_display', read_only=True,
    )

    class Meta:
        model = FormatoInstitucional
        fields = [
            'id', 'slug', 'nombre', 'descripcion',
            'categoria', 'categoria_display',
            'archivo', 'tipo_vinculacion', 'tipo_vinculacion_display',
            'version', 'estado', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_archivo(self, value):
        if value:
            validate_upload_file(value)
        return value
