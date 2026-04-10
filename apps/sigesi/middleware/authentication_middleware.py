import logging
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication as BaseJWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)


class JWTAuthentication(BaseJWTAuthentication):
    """
    Autenticación JWT personalizada que extiende SimpleJWT.
    """

    # Rutas que no requieren autenticación
    EXEMPT_PATHS = [
        '/swagger/',
        '/redoc/',
        '/api/v1/auth/login/',
        '/api/v1/auth/refresh/',
    ]

    def authenticate(self, request):
        # Excluir rutas públicas
        if any(request.path.startswith(path) for path in self.EXEMPT_PATHS):
            return None

        auth_header = request.META.get('HTTP_AUTHORIZATION')

        if not auth_header:
            return None

        # Extraer el token
        if ' ' in auth_header:
            try:
                auth_type, token = auth_header.split(' ', 1)
                if auth_type.lower() != 'bearer':
                    return None
            except ValueError:
                raise AuthenticationFailed(
                    "Cabecera de autorización mal formada")
        else:
            token = auth_header

        # Validar token con SimpleJWT
        try:
            validated_token = self.get_validated_token(token)
        except (InvalidToken, TokenError) as e:
            raise AuthenticationFailed(f"Token inválido: {str(e)}")

        # Obtener usuario del token
        try:
            user = self.get_user(validated_token)
        except AuthenticationFailed:
            raise

        if not user.is_active:
            raise AuthenticationFailed("Usuario inactivo")

        logger.debug("Usuario autenticado: %s (rol: %s)", user, user.rol)

        return (user, validated_token)
