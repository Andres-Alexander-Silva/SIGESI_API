from rest_framework import serializers

from apps.sigesi.models import PerfilInvestigativo, User
from apps.sigesi.serializers.config.user_serializer import UserSerializer


class PerfilInvestigativoListSerializer(serializers.ModelSerializer):
    """Serializador para listar y ver el detalle de un PerfilInvestigativo.

    Embebe la información completa del estudiante asociado (solo lectura) en el
    campo ``estudiante``, de modo que las respuestas de lectura traen el objeto
    del usuario y no únicamente su id.
    """

    estudiante = UserSerializer(read_only=True)

    class Meta:
        model = PerfilInvestigativo
        fields = [
            'id', 'estudiante', 'resumen', 'fortalezas', 'areas_mejora',
            'created_at', 'updated_at',
        ]


class PerfilInvestigativoCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializador para crear y actualizar un PerfilInvestigativo.

    Solo el Administrador escribe perfiles (lo impone
    ``PerfilInvestigativoRolePermission``). No aplica el aval gate del semillero,
    pues el perfil no está atado a un Semillero. Valida que el usuario asociado
    tenga el rol de Estudiante.
    """

    class Meta:
        model = PerfilInvestigativo
        fields = ['estudiante', 'resumen', 'fortalezas', 'areas_mejora']

    def validate_estudiante(self, value):
        """Verifica que el usuario asignado al perfil tenga el rol de Estudiante."""
        if not value.tiene_rol(User.RolChoices.ESTUDIANTE):
            raise serializers.ValidationError(
                'El usuario asignado debe tener el rol de estudiante.'
            )
        return value
