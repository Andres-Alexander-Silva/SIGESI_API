from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import (
    User,
    Semillero,
    Proyecto,
    MatriculaSemillero,
    ProduccionAcademica,
    Actividad,
    Cronograma,
    Evaluacion,
)
from apps.sigesi.utils.time import semestre_actual


SCOPE_ADMINISTRADOR = 'administrador'
SCOPE_GRUPO = 'grupo'
SCOPE_SEMILLERO = 'semillero'

SCOPE_ROLES = {
    SCOPE_ADMINISTRADOR: [User.RolChoices.ADMINISTRADOR],
    SCOPE_GRUPO: [User.RolChoices.DIRECTOR_GRUPO],
    SCOPE_SEMILLERO: [
        User.RolChoices.DIRECTOR_SEMILLERO,
        User.RolChoices.LIDER_ESTUDIANTIL,
        User.RolChoices.ESTUDIANTE,
    ],
}


class DashboardView(APIView):
    """Indicadores agregados para el dashboard principal, filtrados por rol."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary='Indicadores del dashboard',
        operation_description=(
            'Retorna seis contadores agregados (proyectos activos, estudiantes '
            'activos, producción académica, actividades completadas, '
            'cumplimiento semestral y evaluaciones registradas) acotados al '
            'alcance del usuario según su rol.'
        ),
        manual_parameters=[
            openapi.Parameter(
                'semestre',
                openapi.IN_QUERY,
                description="Semestre en formato 'YYYY-1' o 'YYYY-2'. Por defecto el vigente.",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                'scope',
                openapi.IN_QUERY,
                description=(
                    "Alcance solicitado para usuarios con múltiples roles: "
                    "'administrador', 'grupo' o 'semillero'. Si se omite, se "
                    "usa el de mayor privilegio que tenga el usuario."
                ),
                type=openapi.TYPE_STRING,
                enum=[SCOPE_ADMINISTRADOR, SCOPE_GRUPO, SCOPE_SEMILLERO],
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description='Indicadores calculados',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'scope': openapi.Schema(type=openapi.TYPE_STRING),
                        'semestre': openapi.Schema(type=openapi.TYPE_STRING),
                        'proyectos_activos': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'estudiantes_activos': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'produccion_academica': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'actividades_completadas': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'cumplimiento_semestral': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'evaluaciones_registradas': openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
            ),
            400: 'Scope inválido o no permitido para el usuario',
            401: 'No autenticado',
        },
        tags=['Dashboard'],
    )
    def get(self, request):
        user = request.user
        semestre = request.query_params.get('semestre') or semestre_actual()
        scope_solicitado = request.query_params.get('scope')

        if scope_solicitado is not None:
            if scope_solicitado not in SCOPE_ROLES:
                return Response(
                    {'error': "scope inválido. Valores permitidos: 'administrador', 'grupo', 'semillero'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not user.tiene_alguno_de(SCOPE_ROLES[scope_solicitado]):
                return Response(
                    {'error': f"No tienes un rol que habilite el scope '{scope_solicitado}'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        semilleros_scope, scope = self._resolver_alcance(user, scope_solicitado)

        proyectos_activos = Proyecto.objects.filter(
            is_active=True,
            estado__in=[
                Proyecto.EstadoChoices.EN_EJECUCION,
                Proyecto.EstadoChoices.EN_RESULTADOS,
            ],
            semilleros__in=semilleros_scope,
        ).distinct().count()

        estudiantes_activos = MatriculaSemillero.objects.filter(
            semillero__in=semilleros_scope,
            estado=MatriculaSemillero.EstadoChoices.ACTIVA,
            semestre=semestre,
        ).values('estudiante').distinct().count()

        produccion_academica = ProduccionAcademica.objects.filter(
            semillero__in=semilleros_scope,
        ).count()

        actividades_completadas = Actividad.objects.filter(
            estado=Actividad.EstadoChoices.COMPLETADA,
            proyecto__semilleros__in=semilleros_scope,
        ).distinct().count()

        cronogramas_semestre = Cronograma.objects.filter(
            plan_accion__semillero__in=semilleros_scope,
            plan_accion__semestre=semestre,
        )
        total_cronogramas = cronogramas_semestre.count()
        cronogramas_cumplidos = cronogramas_semestre.filter(cumplido=True).count()
        cumplimiento_semestral = (
            round(cronogramas_cumplidos / total_cronogramas * 100, 1)
            if total_cronogramas
            else 0.0
        )

        evaluaciones_registradas = Evaluacion.objects.filter(
            competencia__semillero__in=semilleros_scope,
        ).count()

        return Response(
            {
                'scope': scope,
                'semestre': semestre,
                'proyectos_activos': proyectos_activos,
                'estudiantes_activos': estudiantes_activos,
                'produccion_academica': produccion_academica,
                'actividades_completadas': actividades_completadas,
                'cumplimiento_semestral': cumplimiento_semestral,
                'evaluaciones_registradas': evaluaciones_registradas,
            },
            status=status.HTTP_200_OK,
        )

    def _resolver_alcance(self, user, scope_solicitado=None):
        """Devuelve (queryset de Semilleros visibles, etiqueta de scope).

        Si `scope_solicitado` viene dado, se usa ese alcance (ya validado por
        el caller). Si no, se aplica la precedencia
        administrador > grupo > semillero según los roles del usuario.
        """
        if scope_solicitado == SCOPE_ADMINISTRADOR or (
            scope_solicitado is None and user.tiene_rol(User.RolChoices.ADMINISTRADOR)
        ):
            return Semillero.objects.all(), SCOPE_ADMINISTRADOR

        if scope_solicitado == SCOPE_GRUPO or (
            scope_solicitado is None and user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO)
        ):
            return (
                Semillero.objects.filter(grupo_investigacion__director=user),
                SCOPE_GRUPO,
            )

        if scope_solicitado == SCOPE_SEMILLERO or (
            scope_solicitado is None and user.tiene_alguno_de(SCOPE_ROLES[SCOPE_SEMILLERO])
        ):
            return (
                Semillero.objects.filter(
                    Q(director=user)
                    | Q(lider_estudiantil=user)
                    | Q(
                        matriculas__estudiante=user,
                        matriculas__estado=MatriculaSemillero.EstadoChoices.ACTIVA,
                    )
                ).distinct(),
                SCOPE_SEMILLERO,
            )

        return Semillero.objects.none(), ''
