from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema
from apps.sigesi.models import ProyectoEstudiante, User
from apps.sigesi.serializers.core.proyecto_estudiante_serializer import (
    ProyectoEstudianteListSerializer,
    ProyectoEstudianteCreateUpdateSerializer
)
from apps.sigesi.filters.core.proyecto_estudiante_filter import ProyectoEstudianteFilter
from apps.sigesi.decorators.permissions import ProyectoEstudianteRolePermission
from django.db.models import Q

class ProyectoEstudianteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la gestión de las participaciones de estudiantes en proyectos.
    Permite agregar estudiantes, actualizar sus roles/estado, y consultar su historial.
    """
    permission_classes = [ProyectoEstudianteRolePermission]
    filterset_class = ProyectoEstudianteFilter

    def get_queryset(self):
        """
        Retorna las participaciones según el rol del usuario autenticado:
        - Admin: Todo.
        - Director (Grupo/Semillero): Participaciones en proyectos de su alcance.
        - Líder / Estudiante: Sus propias participaciones y las de proyectos donde participan.
        """
        user = self.request.user
        if not user.is_authenticated:
            return ProyectoEstudiante.objects.none()

        base_qs = ProyectoEstudiante.objects.select_related('proyecto', 'estudiante')

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return base_qs

        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return base_qs.filter(
                proyecto__semilleros__grupo_investigacion__director=user
            ).distinct()

        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return base_qs.filter(
                Q(proyecto__director=user) |
                Q(proyecto__semilleros__director=user)
            ).distinct()

        if user.tiene_rol(User.RolChoices.LIDER_ESTUDIANTIL):
            return base_qs.filter(
                Q(proyecto__lider=user) |
                Q(estudiante=user)
            ).distinct()

        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return base_qs.filter(
                Q(estudiante=user) |
                Q(proyecto__participaciones__estudiante=user)
            ).distinct()

        return ProyectoEstudiante.objects.none()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProyectoEstudianteCreateUpdateSerializer
        return ProyectoEstudianteListSerializer
