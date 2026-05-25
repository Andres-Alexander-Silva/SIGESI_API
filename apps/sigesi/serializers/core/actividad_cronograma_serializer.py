from rest_framework import serializers
from apps.sigesi.models import ActividadCronograma
from apps.sigesi.utils.aval import validar_semilleros_avalados


class ActividadCronogramaListSerializer(serializers.ModelSerializer):
    """Serializador para listar y ver detalle de una ActividadCronograma."""

    responsable_nombre = serializers.CharField(
        source='responsable.get_full_name', read_only=True)

    class Meta:
        model = ActividadCronograma
        fields = [
            'id', 'cronograma', 'titulo', 'descripcion',
            'responsable', 'responsable_nombre',
            'objetivo_general', 'objetivos_especificos', 'estado',
            'fecha_inicio', 'fecha_fin_estimada', 'fecha_fin',
            'created_at', 'updated_at',
        ]


class ActividadCronogramaCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializador para crear y actualizar una ActividadCronograma."""

    class Meta:
        model = ActividadCronograma
        fields = [
            'cronograma', 'titulo', 'descripcion', 'responsable',
            'objetivo_general', 'objetivos_especificos', 'estado',
            'fecha_inicio', 'fecha_fin_estimada', 'fecha_fin',
        ]

    def validate(self, data):
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin_estimada = data.get('fecha_fin_estimada')
        fecha_fin = data.get('fecha_fin')

        if self.instance:
            fecha_inicio = fecha_inicio or self.instance.fecha_inicio
            fecha_fin_estimada = fecha_fin_estimada or self.instance.fecha_fin_estimada
            fecha_fin = fecha_fin if 'fecha_fin' in data else self.instance.fecha_fin

        if fecha_inicio and fecha_fin_estimada and fecha_inicio > fecha_fin_estimada:
            raise serializers.ValidationError({
                "fecha_fin_estimada": "La fecha de fin estimada no puede ser anterior a la fecha de inicio."
            })

        if fecha_fin and fecha_inicio and fecha_fin < fecha_inicio:
            raise serializers.ValidationError({
                "fecha_fin": "La fecha de fin no puede ser anterior a la fecha de inicio."
            })

        # Aval gate: el semillero del cronograma debe tener aval aprobado.
        cronograma = data.get('cronograma') or (
            self.instance.cronograma if self.instance else None)
        if cronograma:
            request = self.context.get('request')
            user = request.user if request else None
            validar_semilleros_avalados(
                [cronograma.plan_accion.semillero], user, field_name='cronograma'
            )

        return data
