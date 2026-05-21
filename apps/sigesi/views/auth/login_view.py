from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from apps.sigesi.serializers.auth.login_serializer import (
    LoginRequestSerializer,
    LoginResponseSerializer,
    RefreshRequestSerializer,
    RefreshResponseSerializer,
    LogoutRequestSerializer,
)
from apps.sigesi.middleware.authentication_middleware import JWTAuthentication
from apps.sigesi.utils.tokens import IdentityToken, build_context_tokens, roles_payload

User = get_user_model()


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(
        operation_summary='Iniciar Sesión',
        request_body=LoginRequestSerializer,
        responses={200: LoginResponseSerializer(), 400: "Credenciales incorrectas"},
        tags=['Auth']
    )
    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = User.objects.filter(email=email).first()

            if not user or not user.check_password(password):
                return Response({"error": "Credenciales incorrectas"}, status=status.HTTP_400_BAD_REQUEST)

            if not user.is_active:
                return Response({"error": "Cuenta inactiva, contacta al administrador"}, status=status.HTTP_403_FORBIDDEN)

            available = roles_payload(user)

            # Auto-selección: con un único rol, emitimos directamente los tokens
            # de contexto (no es necesario el paso /select-role/).
            if len(user.roles) == 1:
                refresh, access = build_context_tokens(user, user.roles[0])
                return Response(
                    {
                        "usuarioId": user.id,
                        "email": user.email,
                        "names": user.get_full_name(),
                        "role": user.roles[0],
                        "available_roles": available,
                        "token": str(access),
                        "refreshToken": str(refresh),
                        "response": "OK",
                    },
                    status=status.HTTP_200_OK
                )

            # Multi-rol (o sin rol): se entrega solo el Identity JWT; el cliente
            # debe llamar a /select-role/ para obtener tokens de contexto.
            identity = IdentityToken.for_user(user)
            return Response(
                {
                    "usuarioId": user.id,
                    "email": user.email,
                    "names": user.get_full_name(),
                    "available_roles": available,
                    "identityToken": str(identity),
                    "response": "SELECT_ROLE",
                },
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RefreshTokenView(APIView):
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(
        operation_summary='Refrescar Token de Sesión',
        request_body=RefreshRequestSerializer,
        responses={
            200: RefreshResponseSerializer(),
            401: "Token inválido o expirado",
        },
        tags=['Auth']
    )
    def post(self, request):
        serializer = RefreshRequestSerializer(data=request.data)
        if serializer.is_valid():
            refresh_token_str = serializer.validated_data['refreshToken']

            try:
                refresh = RefreshToken(refresh_token_str)
                new_access_token = str(refresh.access_token)
                # Si ROTATE_REFRESH_TOKENS=True, se genera un nuevo refresh token
                new_refresh_token = str(refresh)
            except (TokenError, InvalidToken) as e:
                return Response({"error": f"Token inválido o expirado: {str(e)}"}, status=status.HTTP_401_UNAUTHORIZED)

            return Response(
                {
                    "token": new_access_token,
                    "refreshToken": new_refresh_token,
                },
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary='Cerrar Sesión',
        request_body=LogoutRequestSerializer,
        responses={
            204: "Sesión cerrada exitosamente",
            400: "Token inválido",
            401: "No autenticado",
        },
        tags=['Auth']
    )
    def post(self, request):
        serializer = LogoutRequestSerializer(data=request.data)
        if serializer.is_valid():
            refresh_token_str = serializer.validated_data['refreshToken']

            try:
                token = RefreshToken(refresh_token_str)
                token.blacklist()
            except (TokenError, InvalidToken) as e:
                return Response({"error": f"Token inválido: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

