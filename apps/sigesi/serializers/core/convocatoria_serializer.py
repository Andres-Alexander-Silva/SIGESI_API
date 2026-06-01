from rest_framework import serializers

from apps.sigesi.models import Convocatoria
from apps.sigesi.serializers.core.evento_serializer import EventoListSerializer


class ConvocatoriaListSerializer(serializers.ModelSerializer):
    """Serializador de lectura para listar y ver el detalle de una Convocatoria.

    Embebe el evento completo (solo lectura) al que pertenece la convocatoria.
    """

    evento = EventoListSerializer(read_only=True)

    class Meta:
        model = Convocatoria
        fields = [
            'id', 'evento', 'titulo', 'descripcion', 'tipo', 'entidad',
            'fecha_apertura', 'fecha_cierre', 'requisitos', 'presupuesto',
            'url', 'estado', 'created_at', 'updated_at',
        ]


class ConvocatoriaCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializador de creación/actualización de una Convocatoria.

    Solo el Administrador y el Director de Grupo escriben convocatorias (lo
    impone ``ConvocatoriaRolePermission`` en la vista). Cada convocatoria debe
    referirse a un ``evento`` y se valida la coherencia del rango de fechas.
    """

    class Meta:
        model = Convocatoria
        fields = [
            'evento', 'titulo', 'descripcion', 'tipo', 'entidad',
            'fecha_apertura', 'fecha_cierre', 'requisitos', 'presupuesto',
            'url', 'estado',
        ]

    def validate(self, data):
        """Verifica que ``fecha_cierre`` no sea anterior a ``fecha_apertura``."""
        apertura = data.get(
            'fecha_apertura', getattr(self.instance, 'fecha_apertura', None))
        cierre = data.get(
            'fecha_cierre', getattr(self.instance, 'fecha_cierre', None))
        if apertura and cierre and cierre < apertura:
            raise serializers.ValidationError({
                'fecha_cierre': (
                    'La fecha de cierre no puede ser anterior a la fecha de '
                    'apertura.'
                )
            })
        return data
