from rest_framework import serializers
from apps.sigesi.models import Informe, Semillero

class InformeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Informe
        fields = '__all__'
        read_only_fields = ['id', 'generado_por', 'fecha_generacion', 'created_at', 'updated_at', 'contenido']

class GenerarInformeSerializer(serializers.Serializer):
    semillero_id = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=Informe.TipoChoices.choices)
    semestre = serializers.CharField(max_length=10)

    def validate_semillero_id(self, value):
        try:
            Semillero.objects.get(id=value)
        except Semillero.DoesNotExist:
            raise serializers.ValidationError("El semillero especificado no existe.")
        return value
