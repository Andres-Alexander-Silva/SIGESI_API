from rest_framework import serializers

class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

class RoleOptionSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()


class LoginResponseSerializer(serializers.Serializer):
    """Respuesta del login. Dos formas posibles según `response`:

    - `OK` (rol único, auto-seleccionado): incluye `role`, `token`, `refreshToken`.
    - `SELECT_ROLE` (multi-rol): incluye solo `identityToken`; el cliente debe
      llamar a `/auth/select-role/`.
    """
    usuarioId = serializers.IntegerField()
    email = serializers.EmailField()
    names = serializers.CharField()
    available_roles = RoleOptionSerializer(many=True)
    role = serializers.CharField(required=False)
    token = serializers.CharField(required=False)
    refreshToken = serializers.CharField(required=False)
    identityToken = serializers.CharField(required=False)
    response = serializers.CharField()


class SelectRoleRequestSerializer(serializers.Serializer):
    role = serializers.CharField(help_text="Código del rol a activar (ej: administrador).")


class SelectRoleResponseSerializer(serializers.Serializer):
    role = serializers.CharField()
    available_roles = RoleOptionSerializer(many=True)
    token = serializers.CharField()
    refreshToken = serializers.CharField()

class RefreshRequestSerializer(serializers.Serializer):
    refreshToken = serializers.CharField()

class RefreshResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    refreshToken = serializers.CharField()

class LogoutRequestSerializer(serializers.Serializer):
    refreshToken = serializers.CharField()

