from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
import django_filters
from apps.sigesi.models import EvaluacionProyecto, User, Proyecto
from apps.sigesi.serializers.core.evaluacion_proyecto_serializer import EvaluacionProyectoSerializer

class EvaluacionProyectoPermission(permissions.BasePermission):
    """
    Permisos personalizados para Evaluación de Proyectos.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Estudiantes no pueden crear evaluaciones
        if request.method not in permissions.SAFE_METHODS:
            if request.user.tiene_rol(User.RolChoices.ESTUDIANTE) and not request.user.tiene_alguno_de([User.RolChoices.DIRECTOR_GRUPO, User.RolChoices.DIRECTOR_SEMILLERO]):
                return False
                
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True
            
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Modificación/eliminación: Solo el autor (evaluador) o el admin
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            return obj.evaluador == request.user

        return False


class EvaluacionProyectoFilter(django_filters.FilterSet):
    proyecto_id = django_filters.NumberFilter(field_name='proyecto__id')
    evaluador_id = django_filters.NumberFilter(field_name='evaluador__id')
    estado_proyecto = django_filters.CharFilter(field_name='estado_proyecto')

    class Meta:
        model = EvaluacionProyecto
        fields = ['proyecto_id', 'evaluador_id', 'estado_proyecto']


class EvaluacionProyectoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para manejar el CRUD de Evaluaciones de Proyectos.
    """
    swagger_tags = ['Evaluación de Proyectos']  # Sección de documentación (drf-yasg)
    serializer_class = EvaluacionProyectoSerializer
    permission_classes = [permissions.IsAuthenticated, EvaluacionProyectoPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    filterset_class = EvaluacionProyectoFilter
    search_fields = ['observaciones', 'recomendaciones']
    ordering_fields = ['created_at', 'calificacion']

    def get_queryset(self):
        user = self.request.user
        qs = EvaluacionProyecto.objects.all().select_related('proyecto', 'evaluador')

        if not user or not user.is_authenticated:
            return qs.none()

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return qs

        if user.tiene_alguno_de([User.RolChoices.DIRECTOR_GRUPO, User.RolChoices.DIRECTOR_SEMILLERO, User.RolChoices.DOCENTE]):
            # Pueden ver evaluaciones de proyectos de sus semilleros o que dirigen
            return qs.filter(
                Q(evaluador=user) |
                Q(proyecto__director=user) |
                Q(proyecto__semilleros__director=user)
            ).distinct()

        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            # Estudiantes solo ven evaluaciones de los proyectos a los que pertenecen
            return qs.filter(proyecto__estudiantes=user).distinct()

        return qs.none()

    def perform_create(self, serializer):
        proyecto = serializer.validated_data.get('proyecto')
        user = self.request.user

        if not user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            # Validar que sea director del proyecto o de su semillero
            es_director_proyecto = (proyecto.director == user)
            es_director_semillero = proyecto.semilleros.filter(director=user).exists()
            
            if not (es_director_proyecto or es_director_semillero):
                raise PermissionDenied("No tiene permisos para evaluar este proyecto (no es su director ni director de su semillero).")

        serializer.save(evaluador=user)
