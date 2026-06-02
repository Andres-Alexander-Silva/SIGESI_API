from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema

from apps.sigesi.middleware.authentication_middleware import JWTAuthentication
from apps.sigesi.serializers.auth.login_serializer import (
    SelectRoleRequestSerializer,
    SelectRoleResponseSerializer,
)
from apps.sigesi.utils.tokens import build_context_tokens, roles_payload


class SelectRoleView(APIView):
    """Intercambia un Identity JWT *o* un Access JWT por tokens de contexto.

    Acepta ambos tipos de token sin ramificación: los dos son JWT de tipo
    ``access`` firmados con la misma clave, así que ``JWTAuthentication`` valida
    cualquiera y resuelve ``request.user`` desde el claim ``user_id``. Solo se
    exige un token válido (``IsAuthenticated``), no un rol activo — por eso el
    Identity JWT (sin rol) puede llamar a este endpoint, a diferencia del resto.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]   # explícito: NO HasRolePermission

    @swagger_auto_schema(
        operation_summary='Seleccionar / cambiar el rol activo',
        operation_description=(
            'Recibe un `role` (código) y devuelve tokens de contexto definitivos '
            'cuyo access incluye los claims `role` y `available_roles`. Funciona '
            'tanto con el Identity JWT del login como con un Access JWT vigente '
            '(cambio de rol en caliente). Se valida contra la BD que el usuario '
            'realmente posea el rol solicitado.'
        ),
        request_body=SelectRoleRequestSerializer,
        responses={
            200: SelectRoleResponseSerializer(),
            403: 'El usuario no posee el rol solicitado',
        },
        tags=['Autenticación'],
    )
    def post(self, request):
        serializer = SelectRoleRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data['role']

        user = request.user
        # Validación estricta contra BD: el usuario debe poseer el rol solicitado.
        if role not in user.roles:
            return Response(
                {"error": "No tiene asignado el rol solicitado."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh, access = build_context_tokens(user, role)
        return Response(
            {
                "role": role,
                "available_roles": roles_payload(user),
                "token": str(access),
                "refreshToken": str(refresh),
            },
            status=status.HTTP_200_OK,
        )
