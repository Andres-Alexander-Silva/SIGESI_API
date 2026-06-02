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
from apps.sigesi.utils.email_service import enviar_correo_recuperacion_async

User = get_user_model()

class RecuperacionView(APIView):
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(
        operation_summary='Solicitar Recuperación de Contraseña',
        request_body=RecuperacionRequestSerializer,
        responses={
            200: "Solicitud procesada correctamente",
            400: "Errores de validación"
        },
        tags=['Autenticación']
    )
    def post(self, request):
        from django.db.models import Q
        import logging
        logger = logging.getLogger(__name__)

        serializer = RecuperacionRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].strip()
            logger.info(f"Solicitud de recuperación de contraseña recibida para: '{email}'")

            user = User.objects.filter(
                Q(email__iexact=email) | Q(correo_personal__iexact=email)
            ).first()

            if user:
                logger.info(f"Usuario encontrado: {user.username} (activo={user.is_active})")
                if user.is_active:
                    # Crear un token stateless válido por 20 minutos
                    token = AccessToken.for_user(user)
                    token.set_exp(lifetime=timedelta(minutes=20))
                    
                    # Se añade un claim personalizado para identificar que es un token de recuperación
                    token['token_type'] = 'password_recovery'
                    
                    # Determinar el email al que enviar el correo (preferir el institucional si existe)
                    destinatario_email = user.email or user.correo_personal
                    
                    logger.info(f"Enviando correo de recuperación a: {destinatario_email}")
                    # Enviar correo de recuperación
                    # Despacho en segundo plano: el envío SMTP no bloquea la
                    # respuesta. El resultado se registra dentro del hilo; aquí
                    # solo lo evaluamos cuando el envío fue síncrono (res != None).
                    res = enviar_correo_recuperacion_async(
                        destinatario_email=destinatario_email,
                        destinatario_nombre=user.get_full_name(),
                        token=str(token)
                    )
                    if res is not None and res.get("status") != "sent":
                        logger.error(
                            "Fallo al enviar correo de recuperación a %s: %s",
                            destinatario_email, res,
                        )
                else:
                    logger.warning(f"El usuario {user.username} no está activo.")
            else:
                logger.warning(f"No se encontró ningún usuario con el email '{email}' en la base de datos.")

            # Respuesta genérica — no revela si el email existe o no (previene enumeración)
            return Response(
                {"message": "Si el correo existe en nuestro sistema, recibirás un enlace de recuperación."},
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
        tags=['Autenticación']
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
