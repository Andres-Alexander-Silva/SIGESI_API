from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

User = get_user_model()

class RecuperacionRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            'required': 'El correo institucional es obligatorio.',
            'invalid': 'Por favor, ingrese un correo válido.',
            'blank': 'El correo no puede estar vacío.'
        }
    )

    # NOTA: deliberadamente no validamos aquí si el usuario existe ni si está
    # activo. La vista responde de forma genérica para evitar enumeración de
    # correos (ver RecuperacionView.post). Cualquier filtrado real ocurre en
    # la vista al decidir si enviar el correo.

class SetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(
        required=True,
        error_messages={
            'required': 'El token es obligatorio.',
            'blank': 'El token no puede estar vacío.'
        }
    )
    new_password = serializers.CharField(
        required=True,
        min_length=8,
        write_only=True,
        error_messages={
            'required': 'La nueva contraseña es obligatoria.',
            'blank': 'La nueva contraseña no puede estar vacía.',
            'min_length': 'La contraseña debe tener al menos 8 caracteres.'
        }
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        error_messages={
            'required': 'La confirmación de la contraseña es obligatoria.',
            'blank': 'La confirmación de la contraseña no puede estar vacía.'
        }
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Las contraseñas no coinciden."})
        
        token_str = attrs.get('token')
        try:
            token = UntypedToken(token_str)
            if token.get('token_type') != 'password_recovery':
                raise serializers.ValidationError({"token": "El token es inválido para esta operación."})
            attrs['user_id'] = token.get('user_id')
        except (TokenError, InvalidToken):
            raise serializers.ValidationError({"token": "El token es inválido o ha expirado."})
            
        return attrs
