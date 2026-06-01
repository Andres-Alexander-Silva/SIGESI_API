from rest_framework import serializers

from apps.sigesi.models import Evento


class EventoListSerializer(serializers.ModelSerializer):
    """Serializador de lectura para listar y ver el detalle de un Evento."""

    class Meta:
        model = Evento
        fields = [
            'id', 'nombre', 'descripcion', 'modalidad', 'lugar',
            'fecha_inicio', 'fecha_fin', 'estado', 'created_at', 'updated_at',
        ]


class EventoCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializador de creación/actualización de un Evento.

    Solo el Administrador escribe eventos (lo impone ``AdminOrReadOnlyPermission``
    en la vista). Valida la coherencia del rango de fechas.
    """

    class Meta:
        model = Evento
        fields = [
            'nombre', 'descripcion', 'modalidad', 'lugar',
            'fecha_inicio', 'fecha_fin', 'estado',
        ]

    def validate(self, data):
        """Verifica que ``fecha_fin`` no sea anterior a ``fecha_inicio``."""
        inicio = data.get('fecha_inicio', getattr(self.instance, 'fecha_inicio', None))
        fin = data.get('fecha_fin', getattr(self.instance, 'fecha_fin', None))
        if inicio and fin and fin < inicio:
            raise serializers.ValidationError({
                'fecha_fin': 'La fecha de fin no puede ser anterior a la fecha de inicio.'
            })
        return data
