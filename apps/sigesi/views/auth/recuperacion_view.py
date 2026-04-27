from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from rest_framework_simplejwt.tokens import AccessToken
from datetime import timedelta

from apps.sigesi.serializers.auth.recuperacion_serializer import (
    RecuperacionRequestSerializer,
    SetPasswordSerializer
)

User = get_user_model()

class RecuperacionView(APIView):
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(
        operation_summary='Solicitar Recuperación de Contraseña',
        request_body=RecuperacionRequestSerializer,
        responses={
            200: "Token de recuperación generado exitosamente",
            400: "Errores de validación o usuario no encontrado"
        },
        tags=['Auth']
    )
    def post(self, request):
        serializer = RecuperacionRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.filter(email=email).first()

            if user and user.is_active:
                # Crear un token stateless válido por 20 minutos
                token = AccessToken.for_user(user)
                token.set_exp(lifetime=timedelta(minutes=20))
                
                # Se añade un claim personalizado para identificar que es un token de recuperación
                token['token_type'] = 'password_recovery'
                
                # TODO: Implementar el envío de correo electrónico con el token o enlace
                
                return Response(
                    {
                        "message": "Solicitud procesada correctamente.",
                        "token": str(token)  # Temporal: se devuelve el token para verificación
                    },
                    status=status.HTTP_200_OK
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SetPasswordView(APIView):
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(
        operation_summary='Restablecer Contraseña',
        request_body=SetPasswordSerializer,
        responses={
            200: "Contraseña actualizada exitosamente",
            400: "Token inválido o errores en los datos"
        },
        tags=['Auth']
    )
    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data.get('user_id')
            new_password = serializer.validated_data.get('new_password')
            
            user = User.objects.filter(id=user_id).first()
            if not user or not user.is_active:
                return Response(
                    {"error": "Usuario no encontrado o inactivo."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            user.set_password(new_password)
            user.save()
            
            return Response(
                {"message": "Contraseña actualizada correctamente."},
                status=status.HTTP_200_OK
            )
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
