"""Generación de tokens JWT para el flujo de autenticación en dos pasos.

Flujo (Token Exchange):
  1. Login → Identity JWT de vida corta (~5 min) + lista de roles disponibles.
  2. /select-role/ → intercambia el Identity (o un Access vigente) por tokens
     de contexto que llevan los claims `role` y `available_roles`.

Los roles del sistema son códigos de cadena (User.RolChoices), no PKs; por eso
el identificador de rol embebido es el código (p. ej. 'administrador').
"""
from datetime import timedelta

from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.sigesi.models import User


def roles_payload(user):
    """Roles disponibles del usuario, serializables: ``[{'code', 'name'}]``."""
    display = dict(User.RolChoices.choices)
    return [{'code': r, 'name': display.get(r, r)} for r in user.roles]


class IdentityToken(AccessToken):
    """Token de identidad de vida corta (~5 min).

    Solo habilita ``/select-role/``. No contiene el claim ``role``, por lo que
    ``HasRolePermission`` lo rechaza en cualquier endpoint de negocio.
    """
    lifetime = timedelta(minutes=5)

    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        token['token_use'] = 'identity'
        return token


def build_context_tokens(user, role):
    """Genera ``(refresh, access)`` definitivos con ``role`` y ``available_roles``.

    Los claims se fijan en el *refresh*: SimpleJWT los copia al access derivado
    (propiedad ``access_token``) y los conserva al rotar en ``/refresh/``, de modo
    que el flujo de refresco sigue siendo consciente del rol sin cambios.
    """
    refresh = RefreshToken.for_user(user)
    available = roles_payload(user)
    refresh['role'] = role
    refresh['available_roles'] = available
    refresh['token_use'] = 'access'

    access = refresh.access_token  # hereda role / available_roles / token_use
    return refresh, access
