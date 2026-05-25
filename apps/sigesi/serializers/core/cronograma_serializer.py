from rest_framework import serializers
from apps.sigesi.models import Cronograma
from apps.sigesi.utils.aval import validar_semilleros_avalados
from apps.sigesi.serializers.core.actividad_cronograma_serializer import (
    ActividadCronogramaListSerializer,
)


class CronogramaListSerializer(serializers.ModelSerializer):
    """Serializador para listar y ver detalle de un Cronograma."""

    semillero = serializers.IntegerField(
        source='plan_accion.semillero_id', read_only=True)
    semillero_nombre = serializers.CharField(
        source='plan_accion.semillero.nombre', read_only=True)
    semestre = serializers.CharField(
        source='plan_accion.semestre', read_only=True)
    responsable_nombre = serializers.CharField(
        source='responsable.get_full_name', read_only=True)
    actividades = ActividadCronogramaListSerializer(many=True, read_only=True)

    class Meta:
        model = Cronograma
        fields = [
            'id', 'plan_accion', 'semillero', 'semillero_nombre', 'semestre',
            'descripcion', 'responsable', 'responsable_nombre',
            'fecha_inicio', 'fecha_fin', 'cumplido',
            'actividades', 'created_at', 'updated_at',
        ]


class CronogramaCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializador para crear y actualizar un Cronograma."""

    class Meta:
        model = Cronograma
        fields = [
            'plan_accion', 'descripcion', 'responsable',
            'fecha_inicio', 'fecha_fin', 'cumplido',
        ]

    def validate(self, data):
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')

        if self.instance:
            fecha_inicio = fecha_inicio or self.instance.fecha_inicio
            fecha_fin = fecha_fin or self.instance.fecha_fin

        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise serializers.ValidationError({
                "fecha_fin": "La fecha de fin no puede ser anterior a la fecha de inicio."
            })

        # Aval gate: el semillero del plan de acción debe tener aval aprobado.
        plan_accion = data.get('plan_accion') or (
            self.instance.plan_accion if self.instance else None)
        if plan_accion:
            request = self.context.get('request')
            user = request.user if request else None
            validar_semilleros_avalados(
                [plan_accion.semillero], user, field_name='plan_accion'
            )

        return data
