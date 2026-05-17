from rest_framework import serializers
from apps.sigesi.models import Informe, Semillero
from apps.sigesi.utils.aval import validar_semilleros_avalados


class InformeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Informe
        fields = '__all__'
        read_only_fields = ['id', 'generado_por', 'fecha_generacion', 'created_at', 'updated_at', 'contenido']

    def validate(self, data):
        semillero = data.get('semillero') or (self.instance.semillero if self.instance else None)
        if semillero:
            request = self.context.get('request')
            user = request.user if request else None
            validar_semilleros_avalados([semillero], user, field_name='semillero')
        return data


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

    def validate(self, attrs):
        semillero = Semillero.objects.filter(id=attrs.get('semillero_id')).first()
        if semillero:
            request = self.context.get('request')
            user = request.user if request else None
            validar_semilleros_avalados([semillero], user, field_name='semillero_id')
        return attrs
