"""Resolución del alcance de participantes que un usuario puede gestionar.

Centraliza la regla de "qué usuarios puede registrar/gestionar como participante
de un evento" cada rol, para que el serializer (validación en creación), el
``get_queryset`` de la vista (filtro por filas) y la clase de permiso
(``has_object_permission`` en update/delete) compartan exactamente la misma
definición y no se desincronicen.
"""
from django.db import models

from apps.sigesi.models import User, Semillero


def semilleros_en_alcance(user):
    """Devuelve el ``QuerySet`` de Semilleros en los que ``user`` puede gestionar matrículas.

    Es el alcance para *inscribir a otros* (no para autoinscribirse, que admite
    cualquier semillero). Reglas por rol (se acumulan si tiene varios):
    - Administrador: todos los semilleros.
    - Director de Grupo: los semilleros de los grupos que dirige.
    - Director de Semillero: los semilleros que dirige.
    - Líder Estudiantil: los semilleros que lidera.
    - Estudiante (sin rol de gestión): ninguno (solo puede autoinscribirse).
    Cualquier otro caso devuelve un queryset vacío.
    """
    if not user or not user.is_authenticated:
        return Semillero.objects.none()

    if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
        return Semillero.objects.all()

    # Q neutro (no coincide con nada) sobre el que se acumulan los alcances.
    alcance = models.Q(pk__in=[])

    if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
        alcance |= models.Q(grupo_investigacion__director=user)

    if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
        alcance |= models.Q(director=user)

    if user.tiene_rol(User.RolChoices.LIDER_ESTUDIANTIL):
        alcance |= models.Q(lider_estudiantil=user)

    return Semillero.objects.filter(alcance).distinct()


def participantes_en_alcance(user):
    """Devuelve el ``QuerySet`` de Users que ``user`` puede gestionar como participante.

    Reglas por rol (se acumulan si el usuario tiene varios):
    - Administrador: todos los usuarios.
    - Director de Grupo: estudiantes/líderes matriculados en semilleros de su grupo.
    - Director de Semillero: estudiantes/líderes matriculados en su semillero.
    - Líder Estudiantil: estudiantes matriculados en su semillero y él mismo.
    - Estudiante: únicamente él mismo.
    Cualquier otro caso devuelve un queryset vacío.
    """
    if not user or not user.is_authenticated:
        return User.objects.none()

    if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
        return User.objects.all()

    # Q neutro (no coincide con nada) sobre el que se acumulan los alcances.
    alcance = models.Q(pk__in=[])

    if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
        alcance |= models.Q(
            matriculas_semillero__semillero__grupo_investigacion__director=user)

    if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
        alcance |= models.Q(matriculas_semillero__semillero__director=user)

    if user.tiene_rol(User.RolChoices.LIDER_ESTUDIANTIL):
        alcance |= (
            models.Q(matriculas_semillero__semillero__lider_estudiantil=user)
            | models.Q(pk=user.pk)
        )

    if user.tiene_rol(User.RolChoices.ESTUDIANTE):
        alcance |= models.Q(pk=user.pk)

    return User.objects.filter(alcance).distinct()
