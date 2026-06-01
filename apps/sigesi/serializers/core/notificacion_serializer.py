"""Serializadores de lectura para :class:`apps.sigesi.models.Notificacion`."""
from rest_framework import serializers

from apps.sigesi.models import Notificacion


class NotificacionListSerializer(serializers.ModelSerializer):
    """Serializador de lectura de la bandeja de notificaciones de un usuario.

    Expone el ``target`` reducido a ``{kind, id}`` para que el cliente pueda
    navegar al detalle sin necesidad de un serializer polimórfico.
    """

    target = serializers.SerializerMethodField()

    class Meta:
        model = Notificacion
        fields = [
            'id', 'tipo', 'titulo', 'mensaje', 'leida', 'read_at',
            'created_at', 'target',
        ]
        read_only_fields = fields

    def get_target(self, obj):
        """Devuelve ``{kind, id}`` del objeto origen, o ``None``."""
        if obj.content_type_id and obj.object_id:
            return {'kind': obj.content_type.model, 'id': obj.object_id}
        return None
