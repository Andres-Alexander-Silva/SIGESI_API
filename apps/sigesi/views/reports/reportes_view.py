from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, FloatField, Case, When
from django.db.models.functions import Cast
from apps.sigesi.models import Proyecto, Semillero, User
from apps.sigesi.serializers.reports.reportes_serializer import ReporteAcademicoProyectoSerializer, ReporteGlobalSemilleroSerializer

class ReportesAcademicosPermission(permissions.BasePermission):
    """
    Control de acceso a reportes académicos.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

class ReporteAcademicoProyectoList(generics.ListAPIView):
    """
    Consolida información de proyectos incluyendo avances, estado y participación.
    """
    serializer_class = ReporteAcademicoProyectoSerializer
    permission_classes = [permissions.IsAuthenticated, ReportesAcademicosPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'director', 'linea_investigacion']
    search_fields = ['titulo', 'codigo']
    ordering_fields = ['fecha_inicio', 'avance_global']

    def get_queryset(self):
        user = self.request.user
        qs = Proyecto.objects.select_related('director', 'lider').prefetch_related(
            'estudiantes', 'actividades', 'producciones'
        )

        if not user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            if user.tiene_alguno_de([User.RolChoices.DIRECTOR_GRUPO, User.RolChoices.DIRECTOR_SEMILLERO, User.RolChoices.DOCENTE]):
                qs = qs.filter(Q(director=user) | Q(semilleros__director=user)).distinct()
            elif user.tiene_rol(User.RolChoices.ESTUDIANTE):
                qs = qs.filter(estudiantes=user).distinct()
            else:
                qs = qs.none()

        qs = qs.annotate(
            total_actividades=Count('actividades', distinct=True),
            actividades_completadas=Count(
                'actividades', 
                filter=Q(actividades__estado='completada'),
                distinct=True
            ),
            cantidad_producciones=Count('producciones', distinct=True),
            estudiantes_activos_count=Count('estudiantes', distinct=True)
        )
        
        # Evitar division by zero
        qs = qs.annotate(
            avance_global=Case(
                When(total_actividades=0, then=0.0),
                default=Cast('actividades_completadas', FloatField()) * 100.0 / Cast('total_actividades', FloatField()),
                output_field=FloatField()
            )
        )
        return qs

class ReporteGlobalSemilleroList(generics.ListAPIView):
    """
    Consolida información a nivel de Semillero.
    """
    serializer_class = ReporteGlobalSemilleroSerializer
    permission_classes = [permissions.IsAuthenticated, ReportesAcademicosPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['director', 'grupo_investigacion']
    search_fields = ['nombre', 'codigo']

    def get_queryset(self):
        user = self.request.user
        qs = Semillero.objects.select_related('director')

        if not user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            if user.tiene_alguno_de([User.RolChoices.DIRECTOR_GRUPO, User.RolChoices.DIRECTOR_SEMILLERO, User.RolChoices.DOCENTE]):
                qs = qs.filter(Q(director=user) | Q(grupo_investigacion__director=user)).distinct()
            elif user.tiene_rol(User.RolChoices.ESTUDIANTE):
                qs = qs.filter(matriculas__estudiante=user, matriculas__estado='activa').distinct()
            else:
                qs = qs.none()

        qs = qs.annotate(
            total_proyectos=Count('proyectos', distinct=True),
            proyectos_activos=Count(
                'proyectos',
                filter=Q(proyectos__estado__in=['en_ejecucion', 'en_resultados']),
                distinct=True
            ),
            total_matriculas=Count('matriculas', filter=Q(matriculas__estado='activa'), distinct=True),
            total_producciones=Count('producciones', distinct=True)
        )
        return qs
