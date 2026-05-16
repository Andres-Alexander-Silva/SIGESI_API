from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from apps.sigesi.models import Informe, User, Semillero
from apps.sigesi.serializers.reports.informe_serializer import InformeSerializer, GenerarInformeSerializer
from apps.sigesi.services.informes_service import InformesService
import csv

class InformePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        if view.action in ['generar', 'exportar']:
            if request.user.tiene_rol(User.RolChoices.ESTUDIANTE) and not request.user.tiene_alguno_de([User.RolChoices.DIRECTOR_GRUPO, User.RolChoices.DIRECTOR_SEMILLERO]):
                return False
                
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.tiene_rol(User.RolChoices.ADMINISTRADOR) or request.user.tiene_rol(User.RolChoices.DIRECTOR_PROGRAMA):
            return True
            
        if request.user.tiene_alguno_de([User.RolChoices.DIRECTOR_GRUPO, User.RolChoices.DIRECTOR_SEMILLERO, User.RolChoices.DOCENTE]):
            return obj.semillero.director == request.user or obj.semillero.grupo_investigacion.director == request.user
            
        if request.user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return obj.semillero.matriculas.filter(estudiante=request.user, estado='activa').exists()

        return False

class InformeViewSet(viewsets.ModelViewSet):
    queryset = Informe.objects.all().select_related('semillero', 'generado_por')
    serializer_class = InformeSerializer
    permission_classes = [permissions.IsAuthenticated, InformePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['semillero', 'tipo', 'semestre', 'estado']
    search_fields = ['titulo']
    ordering_fields = ['fecha_generacion']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR) or user.tiene_rol(User.RolChoices.DIRECTOR_PROGRAMA):
            return qs

        if user.tiene_alguno_de([User.RolChoices.DIRECTOR_GRUPO, User.RolChoices.DIRECTOR_SEMILLERO, User.RolChoices.DOCENTE]):
            return qs.filter(semillero__director=user) | qs.filter(semillero__grupo_investigacion__director=user)

        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return qs.filter(semillero__matriculas__estudiante=user, semillero__matriculas__estado='activa').distinct()

        return qs.none()

    @action(detail=False, methods=['post'])
    def generar(self, request):
        serializer = GenerarInformeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        semillero_id = serializer.validated_data['semillero_id']
        
        if not request.user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            semillero = Semillero.objects.get(id=semillero_id)
            if semillero.director != request.user and semillero.grupo_investigacion.director != request.user:
                return Response({"detail": "No tiene permisos para generar reportes para este semillero."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            informe = InformesService.generar_informe(
                semillero_id=semillero_id,
                tipo=serializer.validated_data['tipo'],
                semestre=serializer.validated_data['semestre'],
                usuario=request.user
            )
            return Response(InformeSerializer(informe).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def exportar(self, request):
        qs = self.filter_queryset(self.get_queryset())
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="informes_historico.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Titulo', 'Semillero', 'Tipo', 'Semestre', 'Estado', 'Fecha Generacion'])
        
        for informe in qs:
            writer.writerow([
                informe.id,
                informe.titulo,
                informe.semillero.nombre if informe.semillero else '',
                informe.get_tipo_display(),
                informe.semestre,
                informe.get_estado_display(),
                informe.fecha_generacion.strftime('%Y-%m-%d %H:%M:%S') if informe.fecha_generacion else ''
            ])
            
        return response
