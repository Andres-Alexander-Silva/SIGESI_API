"""Endpoints de exportación a xlsx.

Seis APIView, una por recurso. Cada una:
- Filtra por el alcance del usuario (admin / director_grupo / director_semillero).
- Aplica los filtros opcionales de query params.
- Proyecta filas con columnas en español.
- Devuelve un xlsx descargable vía `render_xlsx`.

Estudiante y lider_estudiantil reciben 403 por `ExportarReportesPermission`.
"""
from django.db.models import Q
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import (
    Actividad,
    Evidencia,
    MedicionIndicador,
    ProduccionAcademica,
    Proyecto,
    Semillero,
    User,
)
from apps.sigesi.decorators.permissions import ExportarReportesPermission
from apps.sigesi.utils.xlsx_export import render_xlsx


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scope_semilleros(user):
    """Semilleros visibles al usuario, según rol.

    - Administrador: todos.
    - Director de Grupo: los semilleros de los grupos que dirige.
    - Director de Semillero: los semilleros que dirige.
    - (Cualquier otro: vacío — pero `ExportarReportesPermission` ya bloqueó.)
    """
    if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
        return Semillero.objects.all()
    if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
        return Semillero.objects.filter(grupo_investigacion__director=user)
    if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
        return Semillero.objects.filter(director=user)
    return Semillero.objects.none()


def _full_name(user):
    if user is None:
        return ''
    return (user.get_full_name() or user.email or user.username or '').strip()


def _int_param(request, name):
    """Parsea un query param como int, o devuelve None si está ausente/inválido."""
    raw = request.query_params.get(name)
    if raw is None or raw == '':
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


# Reusable swagger parameter builder
def _qparam(name, description):
    return openapi.Parameter(
        name, openapi.IN_QUERY, description=description,
        type=openapi.TYPE_INTEGER, required=False,
    )


# ---------------------------------------------------------------------------
# 1. Estudiantes
# ---------------------------------------------------------------------------

class ExportEstudiantesView(APIView):
    permission_classes = [ExportarReportesPermission]

    COLUMNS = [
        'Cédula', 'Nombre', 'Apellido', 'Email', 'Correo personal',
        'Programa académico', 'Semillero', 'Semestre', 'Estado matrícula',
        'Fecha inscripción',
    ]

    @swagger_auto_schema(
        operation_summary='Exportar estudiantes a xlsx',
        manual_parameters=[
            _qparam('semillero', 'ID del semillero — una fila por matrícula.'),
            _qparam('proyecto', 'ID del proyecto — una fila por estudiante vinculado al proyecto.'),
        ],
        tags=['Exportar Reportes'],
    )
    def get(self, request):
        semilleros_scope = _scope_semilleros(request.user)
        semillero_id = _int_param(request, 'semillero')
        proyecto_id = _int_param(request, 'proyecto')

        rows = []

        if semillero_id is not None:
            from apps.sigesi.models import MatriculaSemillero
            qs = (
                MatriculaSemillero.objects
                .filter(semillero__in=semilleros_scope, semillero_id=semillero_id)
                .select_related('estudiante', 'estudiante__programa_academico', 'semillero')
                .order_by('estudiante__last_name', 'estudiante__first_name')
            )
            for m in qs:
                e = m.estudiante
                programa = e.programa_academico.nombre if e.programa_academico_id else ''
                rows.append([
                    e.cedula, e.first_name, e.last_name, e.email, e.correo_personal,
                    programa, m.semillero.nombre, m.semestre, m.estado, m.fecha_inscripcion,
                ])
        elif proyecto_id is not None:
            proyecto = (
                Proyecto.objects
                .filter(semilleros__in=semilleros_scope, id=proyecto_id)
                .first()
            )
            if proyecto is not None:
                for e in proyecto.estudiantes.select_related('programa_academico').all():
                    programa = e.programa_academico.nombre if e.programa_academico_id else ''
                    rows.append([
                        e.cedula, e.first_name, e.last_name, e.email, e.correo_personal,
                        programa, '', '', '', None,
                    ])
        else:
            qs = (
                User.objects
                .filter(roles__contains=[User.RolChoices.ESTUDIANTE])
                .select_related('programa_academico')
                .order_by('last_name', 'first_name')
            )
            # Si no es admin, restringir a estudiantes con matrícula en sus semilleros
            if not request.user.tiene_rol(User.RolChoices.ADMINISTRADOR):
                qs = qs.filter(matriculas_semillero__semillero__in=semilleros_scope).distinct()
            for e in qs:
                programa = e.programa_academico.nombre if e.programa_academico_id else ''
                rows.append([
                    e.cedula, e.first_name, e.last_name, e.email, e.correo_personal,
                    programa, '', '', '', None,
                ])

        return render_xlsx('estudiantes', self.COLUMNS, rows)


# ---------------------------------------------------------------------------
# 2. Proyectos
# ---------------------------------------------------------------------------

class ExportProyectosView(APIView):
    permission_classes = [ExportarReportesPermission]

    COLUMNS = [
        'Código', 'Título', 'Estado', 'Línea de investigación',
        'Director', 'Líder', 'Semilleros', 'Grupo de investigación',
        'Fecha inicio', 'Fecha fin estimada', 'Fecha cierre', 'Activo',
    ]

    @swagger_auto_schema(
        operation_summary='Exportar proyectos a xlsx',
        manual_parameters=[
            _qparam('semillero', 'ID del semillero al que pertenece el proyecto.'),
            _qparam('linea_investigacion', 'ID de la línea de investigación.'),
            _qparam('grupo_investigacion', 'ID del grupo de investigación (vía semilleros).'),
        ],
        tags=['Exportar Reportes'],
    )
    def get(self, request):
        semilleros_scope = _scope_semilleros(request.user)

        qs = (
            Proyecto.objects
            .filter(semilleros__in=semilleros_scope)
            .select_related('director', 'lider', 'linea_investigacion')
            .prefetch_related('semilleros', 'semilleros__grupo_investigacion')
            .distinct()
            .order_by('-created_at')
        )

        sem_id = _int_param(request, 'semillero')
        if sem_id is not None:
            qs = qs.filter(semilleros__id=sem_id)
        linea_id = _int_param(request, 'linea_investigacion')
        if linea_id is not None:
            qs = qs.filter(linea_investigacion_id=linea_id)
        grupo_id = _int_param(request, 'grupo_investigacion')
        if grupo_id is not None:
            qs = qs.filter(semilleros__grupo_investigacion_id=grupo_id)

        rows = []
        for p in qs.distinct():
            semilleros = list(p.semilleros.all())
            semilleros_nombres = ', '.join(s.nombre for s in semilleros)
            grupos_nombres = ', '.join({
                s.grupo_investigacion.nombre for s in semilleros if s.grupo_investigacion_id
            })
            rows.append([
                p.codigo, p.titulo, p.estado,
                p.linea_investigacion.nombre if p.linea_investigacion_id else '',
                _full_name(p.director), _full_name(p.lider),
                semilleros_nombres, grupos_nombres,
                p.fecha_inicio, p.fecha_fin_estimada, p.fecha_cierre, p.is_active,
            ])

        return render_xlsx('proyectos', self.COLUMNS, rows)


# ---------------------------------------------------------------------------
# 3. Avances (Evidencia)
# ---------------------------------------------------------------------------

class ExportAvancesView(APIView):
    permission_classes = [ExportarReportesPermission]

    COLUMNS = [
        'Título', 'Tipo', 'Descripción', 'URL archivo',
        'Actividad', 'Proyecto', 'Subido por', 'Fecha creación',
    ]

    @swagger_auto_schema(
        operation_summary='Exportar avances (evidencias) a xlsx',
        manual_parameters=[
            _qparam('semillero', 'ID del semillero (vía proyecto del avance).'),
            _qparam('proyecto', 'ID del proyecto.'),
            _qparam('user', 'ID del usuario que subió el avance.'),
            _qparam('actividad', 'ID de la actividad.'),
        ],
        tags=['Exportar Reportes'],
    )
    def get(self, request):
        semilleros_scope = _scope_semilleros(request.user)

        qs = (
            Evidencia.objects
            .filter(actividad__proyecto__semilleros__in=semilleros_scope)
            .select_related('actividad', 'actividad__proyecto', 'subido_por')
            .distinct()
            .order_by('-created_at')
        )

        sem_id = _int_param(request, 'semillero')
        if sem_id is not None:
            qs = qs.filter(actividad__proyecto__semilleros__id=sem_id)
        proyecto_id = _int_param(request, 'proyecto')
        if proyecto_id is not None:
            qs = qs.filter(actividad__proyecto_id=proyecto_id)
        user_id = _int_param(request, 'user')
        if user_id is not None:
            qs = qs.filter(subido_por_id=user_id)
        actividad_id = _int_param(request, 'actividad')
        if actividad_id is not None:
            qs = qs.filter(actividad_id=actividad_id)

        rows = []
        for e in qs.distinct():
            archivo_url = ''
            if e.archivo:
                try:
                    archivo_url = request.build_absolute_uri(e.archivo.url)
                except ValueError:
                    archivo_url = ''
            rows.append([
                e.titulo, e.tipo, e.descripcion, archivo_url,
                e.actividad.titulo if e.actividad_id else '',
                e.actividad.proyecto.titulo if e.actividad_id and e.actividad.proyecto_id else '',
                _full_name(e.subido_por), e.created_at,
            ])

        return render_xlsx('avances', self.COLUMNS, rows)


# ---------------------------------------------------------------------------
# 4. Producción Académica
# ---------------------------------------------------------------------------

class ExportProduccionesAcademicasView(APIView):
    permission_classes = [ExportarReportesPermission]

    COLUMNS = [
        'Título', 'Tipo', 'Estado', 'Proyecto', 'Semillero',
        'Línea de investigación', 'Autores', 'DOI', 'Revista/Evento',
        'Fecha publicación', 'Fecha creación',
    ]

    @swagger_auto_schema(
        operation_summary='Exportar producciones académicas a xlsx',
        manual_parameters=[
            _qparam('proyecto', 'ID del proyecto.'),
            _qparam('semillero', 'ID del semillero.'),
            _qparam('linea_investigacion', 'ID de la línea de investigación.'),
            _qparam('grupo_investigacion', 'ID del grupo (vía semillero.grupo_investigacion).'),
            _qparam('user', 'ID de un autor (M2M autores).'),
        ],
        tags=['Exportar Reportes'],
    )
    def get(self, request):
        semilleros_scope = _scope_semilleros(request.user)

        qs = (
            ProduccionAcademica.objects
            .filter(semillero__in=semilleros_scope)
            .select_related('proyecto', 'semillero', 'linea_investigacion')
            .prefetch_related('autores')
            .distinct()
            .order_by('-fecha_publicacion', '-created_at')
        )

        proyecto_id = _int_param(request, 'proyecto')
        if proyecto_id is not None:
            qs = qs.filter(proyecto_id=proyecto_id)
        sem_id = _int_param(request, 'semillero')
        if sem_id is not None:
            qs = qs.filter(semillero_id=sem_id)
        linea_id = _int_param(request, 'linea_investigacion')
        if linea_id is not None:
            qs = qs.filter(linea_investigacion_id=linea_id)
        grupo_id = _int_param(request, 'grupo_investigacion')
        if grupo_id is not None:
            qs = qs.filter(semillero__grupo_investigacion_id=grupo_id)
        user_id = _int_param(request, 'user')
        if user_id is not None:
            qs = qs.filter(autores__id=user_id)

        rows = []
        for p in qs.distinct():
            autores = ', '.join(_full_name(a) for a in p.autores.all())
            rows.append([
                p.titulo, p.tipo, p.estado,
                p.proyecto.titulo if p.proyecto_id else '',
                p.semillero.nombre if p.semillero_id else '',
                p.linea_investigacion.nombre if p.linea_investigacion_id else '',
                autores, p.doi, p.revista_evento,
                p.fecha_publicacion, p.created_at,
            ])

        return render_xlsx('producciones_academicas', self.COLUMNS, rows)


# ---------------------------------------------------------------------------
# 5. Actividades
# ---------------------------------------------------------------------------

class ExportActividadesView(APIView):
    permission_classes = [ExportarReportesPermission]

    COLUMNS = [
        'Proyecto', 'Título', 'Descripción', 'Responsable',
        'Fecha inicio', 'Fecha fin', 'Estado', 'Porcentaje avance',
    ]

    @swagger_auto_schema(
        operation_summary='Exportar actividades a xlsx',
        manual_parameters=[
            _qparam('user', 'ID del responsable.'),
            _qparam('proyecto', 'ID del proyecto.'),
            _qparam('semillero', 'ID del semillero (vía proyecto).'),
        ],
        tags=['Exportar Reportes'],
    )
    def get(self, request):
        semilleros_scope = _scope_semilleros(request.user)

        qs = (
            Actividad.objects
            .filter(proyecto__semilleros__in=semilleros_scope)
            .select_related('proyecto', 'responsable')
            .distinct()
            .order_by('proyecto', 'fecha_inicio')
        )

        user_id = _int_param(request, 'user')
        if user_id is not None:
            qs = qs.filter(responsable_id=user_id)
        proyecto_id = _int_param(request, 'proyecto')
        if proyecto_id is not None:
            qs = qs.filter(proyecto_id=proyecto_id)
        sem_id = _int_param(request, 'semillero')
        if sem_id is not None:
            qs = qs.filter(proyecto__semilleros__id=sem_id)

        rows = []
        for a in qs.distinct():
            rows.append([
                a.proyecto.titulo if a.proyecto_id else '',
                a.titulo, a.descripcion, _full_name(a.responsable),
                a.fecha_inicio, a.fecha_fin, a.estado, a.porcentaje_avance,
            ])

        return render_xlsx('actividades', self.COLUMNS, rows)


# ---------------------------------------------------------------------------
# 6. Indicadores
# ---------------------------------------------------------------------------

class ExportIndicadoresView(APIView):
    permission_classes = [ExportarReportesPermission]

    COLUMNS = [
        'Indicador', 'Categoría', 'Semillero', 'Semestre', 'Valor',
        'Unidad de medida', 'Meta', 'Observaciones', 'Registrado por',
        'Fecha creación',
    ]

    @swagger_auto_schema(
        operation_summary='Exportar mediciones de indicadores a xlsx',
        manual_parameters=[
            _qparam('semillero', 'ID del semillero.'),
        ],
        tags=['Exportar Reportes'],
    )
    def get(self, request):
        semilleros_scope = _scope_semilleros(request.user)

        qs = (
            MedicionIndicador.objects
            .filter(semillero__in=semilleros_scope)
            .select_related('indicador', 'semillero', 'registrado_por')
            .order_by('semillero', '-semestre', 'indicador__nombre')
        )

        sem_id = _int_param(request, 'semillero')
        if sem_id is not None:
            qs = qs.filter(semillero_id=sem_id)

        rows = []
        for m in qs:
            ind = m.indicador
            rows.append([
                ind.nombre, ind.get_categoria_display(),
                m.semillero.nombre, m.semestre, m.valor,
                ind.unidad_medida, ind.meta,
                m.observaciones, _full_name(m.registrado_por),
                m.created_at,
            ])

        return render_xlsx('indicadores', self.COLUMNS, rows)
