from typing import Iterable, Optional

from rest_framework import serializers

from apps.sigesi.models import Semillero, User


def validar_semilleros_avalados(
    semilleros: Iterable[Semillero],
    user: Optional[User],
    field_name: str = 'semilleros',
) -> None:
    """Lanza ``ValidationError`` si algún Semillero no tiene aval aprobado.

    Args:
        semilleros: Iterable de instancias ``Semillero`` ya cargadas a validar.
        user: Usuario que realiza la acción; el administrador omite la regla.
        field_name: Clave bajo la cual se reporta el error de validación.

    Raises:
        rest_framework.serializers.ValidationError: Si uno o más semilleros no
            están en estado de aval ``aprobado`` (y el usuario no es admin).
    """
    if user and user.is_authenticated and user.tiene_rol(User.RolChoices.ADMINISTRADOR):
        return

    pendientes = [
        s for s in semilleros
        if s.estado_aval != Semillero.EstadoAvalChoices.APROBADO
    ]
    if pendientes:
        nombres = ", ".join(s.nombre for s in pendientes)
        raise serializers.ValidationError({
            field_name: (
                "No se pueden realizar acciones sobre semilleros sin aval "
                f"aprobado: {nombres}."
            )
        })
