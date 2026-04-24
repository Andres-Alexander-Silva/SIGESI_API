from rest_framework import serializers
from django.contrib.auth import get_user_model

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

    def validate_email(self, value):
        # Verificar si el usuario existe y está activo
        user = User.objects.filter(email=value).first()
        
        if not user:
            raise serializers.ValidationError("No existe un usuario con este correo institucional.")
        
        if not user.is_active:
            raise serializers.ValidationError("La cuenta asociada a este correo se encuentra inactiva.")
            
        return value
