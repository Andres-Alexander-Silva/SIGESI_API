"""Serializador de lectura para :class:`apps.sigesi.models.RegistroAuditoria`."""
from rest_framework import serializers

from apps.sigesi.models import RegistroAuditoria


class RegistroAuditoriaSerializer(serializers.ModelSerializer):
    """Serializador de solo lectura de la traza de auditoría.

    Expone ``usuario`` (el correo snapshot, ``usuario_email``) además del resto
    de metadatos de trazabilidad. La respuesta del endpoint envuelve estos datos
    en el sobre ``{success, data}``.
    """

    usuario = serializers.CharField(source='usuario_email', read_only=True)

    class Meta:
        model = RegistroAuditoria
        fields = [
            'id', 'accion', 'modulo', 'usuario', 'rol_activo',
            'metodo_http', 'ruta', 'status_code', 'object_id',
            'ip', 'user_agent', 'fecha',
        ]
        read_only_fields = fields
