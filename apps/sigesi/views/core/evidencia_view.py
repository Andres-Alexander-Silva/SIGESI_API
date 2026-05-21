from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
import django_filters
from apps.sigesi.models import Evidencia, User, Proyecto
from apps.sigesi.serializers.core.evidencia_serializer import EvidenciaSerializer
from apps.sigesi.utils.download import ArchiveDownloadMixin, ArchiveUploadMixin

class EvidenciaPermission(permissions.BasePermission):
    """
    Permisos personalizados para Evidencia (Avances).
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Admin can do anything
        if request.user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True
            
        # Para ver (GET)
        if request.method in permissions.SAFE_METHODS:
            # Estudiante: solo sus propios archivos
            if request.user.tiene_rol(User.RolChoices.ESTUDIANTE) and not request.user.tiene_alguno_de([User.RolChoices.DIRECTOR_GRUPO, User.RolChoices.DIRECTOR_SEMILLERO, User.RolChoices.LIDER_ESTUDIANTIL]):
                return obj.subido_por == request.user
            # Director/Lider: pueden ver si dirigen el proyecto o si son parte
            proyecto = obj.actividad.proyecto
            is_director_or_lider = (proyecto.director == request.user or proyecto.lider == request.user)
            if is_director_or_lider:
                return True
            return obj.subido_por == request.user

        # Para modificar/eliminar
        if request.user.tiene_rol(User.RolChoices.ESTUDIANTE) and not request.user.tiene_alguno_de([User.RolChoices.DIRECTOR_GRUPO, User.RolChoices.DIRECTOR_SEMILLERO]):
            return obj.subido_por == request.user

        # Director puede agregar observaciones (actualizar)
        if request.method in ['PUT', 'PATCH']:
            proyecto = obj.actividad.proyecto
            if proyecto.director == request.user or proyecto.lider == request.user:
                return True

        return obj.subido_por == request.user


class EvidenciaFilter(django_filters.FilterSet):
    proyecto_id = django_filters.NumberFilter(field_name='actividad__proyecto__id')
    usuario_id = django_filters.NumberFilter(field_name='subido_por__id')
    estado = django_filters.CharFilter(field_name='actividad__estado')

    class Meta:
        model = Evidencia
        fields = ['proyecto_id', 'usuario_id', 'estado', 'tipo']


class EvidenciaViewSet(ArchiveDownloadMixin, ArchiveUploadMixin, viewsets.ModelViewSet):
    """
    ViewSet para manejar el CRUD de Evidencias (Avances).
    """
    serializer_class = EvidenciaSerializer
    permission_classes = [permissions.IsAuthenticated, EvidenciaPermission]
    archive_field = 'archivo'
    upload_serializer_class = EvidenciaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    filterset_class = EvidenciaFilter
    search_fields = ['titulo', 'descripcion']
    ordering_fields = ['created_at', 'updated_at']

    def list(self, request, *args, **kwargs):
        proyecto_id = request.query_params.get('proyecto_id')
        usuario_id = request.query_params.get('usuario_id')
        
        if proyecto_id:
            try:
                proyecto = Proyecto.objects.get(id=proyecto_id)
            except Proyecto.DoesNotExist:
                return Response({"detail": "El proyecto referenciado no existe."}, status=status.HTTP_404_NOT_FOUND)
                
            if usuario_id:
                try:
                    usuario = User.objects.get(id=usuario_id)
                except User.DoesNotExist:
                    return Response({"detail": "El usuario referenciado no existe."}, status=status.HTTP_404_NOT_FOUND)
                
                es_estudiante_vinculado = proyecto.estudiantes.filter(id=usuario.id).exists()
                es_director_o_lider = (proyecto.director == usuario or proyecto.lider == usuario)
                
                if not (es_estudiante_vinculado or es_director_o_lider):
                    return Response({"detail": "El usuario no pertenece al proyecto."}, status=status.HTTP_400_BAD_REQUEST)
                    
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        qs = Evidencia.objects.all().select_related('actividad', 'actividad__proyecto', 'subido_por')

        if not user or not user.is_authenticated:
            return qs.none()

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return qs

        # Director o Lider
        if user.tiene_alguno_de([User.RolChoices.DIRECTOR_GRUPO, User.RolChoices.DIRECTOR_SEMILLERO, User.RolChoices.LIDER_ESTUDIANTIL]):
            # Pueden ver las suyas y las de los proyectos donde son director o lider
            return qs.filter(
                Q(subido_por=user) |
                Q(actividad__proyecto__director=user) |
                Q(actividad__proyecto__lider=user)
            ).distinct()

        # Estudiante
        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return qs.filter(subido_por=user)

        return qs.filter(subido_por=user)

    def perform_create(self, serializer):
        actividad = serializer.validated_data.get('actividad')
        proyecto = actividad.proyecto
        user = self.request.user

        # Validar que el usuario pertenezca al proyecto
        if not user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            es_estudiante_vinculado = proyecto.estudiantes.filter(id=user.id).exists()
            es_director_o_lider = (proyecto.director == user or proyecto.lider == user)
            
            if not (es_estudiante_vinculado or es_director_o_lider):
                raise PermissionDenied("El usuario no pertenece al proyecto sobre el que intenta registrar el avance.")

        serializer.save(subido_por=user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # "eliminar un avance sin evidencias asociadas" -> No aplica estrictamente dado el modelo,
        # pero permitiremos eliminar la Evidencia normalmente.
        if instance.archivo:
            # Archivo se eliminará al eliminar el registro (usualmente se maneja por signals o django-cleanup, 
            # pero aquí borramos el registro).
            pass
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
