from rest_framework import serializers

from apps.sigesi.models import Semillero, User


def validar_semilleros_avalados(semilleros, user, field_name='semilleros'):
    """Lanza ValidationError si algún Semillero no tiene aval aprobado.

    El administrador puede continuar siempre. `semilleros` debe ser una lista o
    iterable de instancias `Semillero` ya cargadas.
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
