from rest_framework import serializers
from apps.sigesi.models import CronogramaProyecto


class CronogramaProyectoListSerializer(serializers.ModelSerializer):
    """Serializador para listar y ver detalle de un CronogramaProyecto."""

    proyecto_titulo = serializers.CharField(source='proyecto.titulo', read_only=True)

    class Meta:
        model = CronogramaProyecto
        fields = [
            'id', 'proyecto', 'proyecto_titulo',
            'actividad', 'descripcion_actividad',
            'fecha_inicio', 'fecha_fin', 'fecha_entrega',
            'estado_actividad', 'archivo_cronograma', 'observaciones',
            'created_at', 'updated_at',
        ]


class CronogramaProyectoCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializador para crear y actualizar un CronogramaProyecto."""

    class Meta:
        model = CronogramaProyecto
        fields = [
            'proyecto',
            'actividad', 'descripcion_actividad',
            'fecha_inicio', 'fecha_fin', 'fecha_entrega',
            'estado_actividad', 'archivo_cronograma', 'observaciones',
        ]

    def validate(self, data):
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        fecha_entrega = data.get('fecha_entrega')

        if self.instance:
            fecha_inicio = fecha_inicio or self.instance.fecha_inicio
            fecha_fin = fecha_fin or self.instance.fecha_fin
            fecha_entrega = fecha_entrega or self.instance.fecha_entrega

        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise serializers.ValidationError({
                "fecha_fin": "La fecha de fin no puede ser anterior a la fecha de inicio."
            })

        if fecha_entrega and fecha_inicio and fecha_entrega < fecha_inicio:
            raise serializers.ValidationError({
                "fecha_entrega": "La fecha de entrega no puede ser anterior a la fecha de inicio."
            })

        return data
