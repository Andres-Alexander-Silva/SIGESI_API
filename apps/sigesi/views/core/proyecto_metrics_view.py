from collections import Counter

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import (
    Proyecto,
    FaseProyecto,
    Actividad,
    Alerta,
    CronogramaProyecto,
    User,
)
from apps.sigesi.utils.time import get_now_colombia


SCOPE_ADMINISTRADOR = 'administrador'
SCOPE_GRUPO = 'grupo'
SCOPE_SEMILLERO = 'semillero'
SCOPE_ESTUDIANTE = 'estudiante'


class ProyectoMetricsDashboardView(APIView):
    """Tabla de métricas por proyecto + resumen de alcance, acotada por rol."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary='Métricas dashboard por proyecto',
        operation_description=(
            'Retorna, para cada proyecto visible al usuario, su porcentaje de '
            'progreso (por fases), actividades realizadas, alertas, estados de '
            'cronograma y otras métricas, junto con un resumen agregado del '
            'alcance.'
        ),
        manual_parameters=[
            openapi.Parameter(
                'proyecto',
                openapi.IN_QUERY,
                description='ID del proyecto a consultar (opcional, debe estar dentro del alcance del usuario).',
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(description='Métricas calculadas'),
            400: 'proyecto inválido',
            401: 'No autenticado',
        },
        tags=['Dashboard'],
    )
    def get(self, request):
        user = request.user
        proyectos_scope, scope = self._resolver_alcance(user)

        proyecto_id_raw = request.query_params.get('proyecto')
        if proyecto_id_raw is not None:
            try:
                proyecto_id = int(proyecto_id_raw)
            except ValueError:
                return Response(
                    {'error': "El query param 'proyecto' debe ser un entero."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            proyectos_scope = proyectos_scope.filter(id=proyecto_id)

        proyectos_qs = (
            proyectos_scope
            .select_related('director', 'lider')
            .prefetch_related('alertas', 'cronogramas')
            .annotate(
                total_fases=Count('fases', distinct=True),
                fases_completadas=Count(
                    'fases',
                    filter=Q(fases__estado=FaseProyecto.EstadoChoices.COMPLETADA),
                    distinct=True,
                ),
                total_actividades=Count('actividades', distinct=True),
                actividades_completadas=Count(
                    'actividades',
                    filter=Q(actividades__estado=Actividad.EstadoChoices.COMPLETADA),
                    distinct=True,
                ),
                alertas_total_ann=Count('alertas', distinct=True),
                alertas_no_leidas_ann=Count(
                    'alertas',
                    filter=Q(alertas__leida=False),
                    distinct=True,
                ),
                estudiantes_count=Count('estudiantes', distinct=True),
                producciones_academicas_count=Count('producciones', distinct=True),
            )
            .order_by('titulo')
        )

        hoy = get_now_colombia().date()

        proyectos_payload = []
        proyectos_con_alertas = 0
        progreso_acumulado = 0.0

        for proyecto in proyectos_qs:
            porcentaje_progreso = (
                round(proyecto.fases_completadas / proyecto.total_fases * 100, 1)
                if proyecto.total_fases else 0.0
            )

            alertas_por_prioridad = self._contar_por(
                proyecto.alertas.all(),
                attr='prioridad',
                keys=[c.value for c in Alerta.PrioridadChoices],
            )

            cronograma_estados = self._contar_por(
                proyecto.cronogramas.all(),
                attr='estado_actividad',
                keys=[c.value for c in CronogramaProyecto.EstadoChoices],
            )

            total_cronogramas = sum(cronograma_estados.values())
            cumplidas = cronograma_estados.get(
                CronogramaProyecto.EstadoChoices.COMPLETADA.value, 0
            )
            cronograma_porcentaje_cumplimiento = (
                round(cumplidas / total_cronogramas * 100, 1)
                if total_cronogramas else 0.0
            )

            dias_restantes = (
                (proyecto.fecha_fin_estimada - hoy).days
                if proyecto.fecha_fin_estimada else None
            )

            if proyecto.alertas_total_ann > 0:
                proyectos_con_alertas += 1
            progreso_acumulado += porcentaje_progreso

            proyectos_payload.append({
                'id': proyecto.id,
                'titulo': proyecto.titulo,
                'codigo': proyecto.codigo,
                'estado': proyecto.estado,
                'porcentaje_progreso': porcentaje_progreso,
                'fases_completadas': proyecto.fases_completadas,
                'total_fases': proyecto.total_fases,
                'actividades_completadas': proyecto.actividades_completadas,
                'total_actividades': proyecto.total_actividades,
                'alertas_total': proyecto.alertas_total_ann,
                'alertas_no_leidas': proyecto.alertas_no_leidas_ann,
                'alertas_por_prioridad': alertas_por_prioridad,
                'cronograma_estados': cronograma_estados,
                'cronograma_porcentaje_cumplimiento': cronograma_porcentaje_cumplimiento,
                'estudiantes_count': proyecto.estudiantes_count,
                'producciones_academicas_count': proyecto.producciones_academicas_count,
                'dias_restantes': dias_restantes,
            })

        total_proyectos = len(proyectos_payload)
        porcentaje_alertas = (
            round(proyectos_con_alertas / total_proyectos * 100, 1)
            if total_proyectos else 0.0
        )
        porcentaje_progreso_promedio = (
            round(progreso_acumulado / total_proyectos, 1)
            if total_proyectos else 0.0
        )

        return Response(
            {
                'scope': scope,
                'scope_summary': {
                    'total_proyectos': total_proyectos,
                    'proyectos_con_alertas': proyectos_con_alertas,
                    'porcentaje_proyectos_con_alertas': porcentaje_alertas,
                    'porcentaje_progreso_promedio': porcentaje_progreso_promedio,
                },
                'proyectos': proyectos_payload,
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _contar_por(items, attr, keys):
        """Cuenta items por el atributo dado, asegurando que todas las keys estén presentes."""
        contador = Counter(getattr(item, attr) for item in items)
        return {key: contador.get(key, 0) for key in keys}

    def _resolver_alcance(self, user):
        """Devuelve (queryset de Proyectos visibles, etiqueta de scope) según rol.

        Replica la jerarquía usada en proyecto_view.py (admin > grupo >
        semillero > estudiante). El alcance es sobre Proyecto.is_active=True.
        """
        base = Proyecto.objects.filter(is_active=True)

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return base, SCOPE_ADMINISTRADOR

        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return (
                base.filter(
                    Q(director=user)
                    | Q(semilleros__director=user)
                    | Q(semilleros__grupo_investigacion__director=user)
                ).distinct(),
                SCOPE_GRUPO,
            )

        if user.tiene_alguno_de([
            User.RolChoices.DIRECTOR_SEMILLERO,
            User.RolChoices.LIDER_ESTUDIANTIL,
        ]):
            return (
                base.filter(
                    Q(director=user)
                    | Q(lider=user)
                    | Q(estudiantes=user)
                    | Q(semilleros__director=user)
                    | Q(semilleros__lider_estudiantil=user)
                ).distinct(),
                SCOPE_SEMILLERO,
            )

        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return (
                base.filter(
                    Q(lider=user) | Q(estudiantes=user)
                ).distinct(),
                SCOPE_ESTUDIANTE,
            )

        return base.none(), ''
