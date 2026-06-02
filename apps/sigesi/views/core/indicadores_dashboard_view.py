"""Dashboard de indicadores generales por semillero."""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import User, Semillero, Proyecto


class IndicadoresDashboardPermission(IsAuthenticated):
    """Permiso para el dashboard de indicadores.

    Acceso: administrador (cualquier semillero),
    director_grupo (semilleros de su grupo),
    director_semillero (sus propios semilleros).
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.tiene_alguno_de([
            User.RolChoices.ADMINISTRADOR,
            User.RolChoices.DIRECTOR_GRUPO,
            User.RolChoices.DIRECTOR_SEMILLERO,
        ])


def _semillero_visible_para(user, semillero_id):
    """Verifica si el usuario puede ver datos del semillero dado."""
    if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
        return True
    if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
        return Semillero.objects.filter(
            pk=semillero_id,
            grupo_investigacion__director=user,
        ).exists()
    if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
        return Semillero.objects.filter(pk=semillero_id, director=user).exists()
    return False


class IndicadoresDashboardView(APIView):
    """Indicadores generales: proyectos activos y finalizados de un semillero.

    Solo usuarios con rol administrador, director_grupo o director_semillero
    tienen acceso.
    """

    permission_classes = [IndicadoresDashboardPermission]

    @swagger_auto_schema(
        operation_summary='Indicadores generales de semillero',
        operation_description=(
            'Retorna el conteo de proyectos activos (en_ejecucion / en_resultados) '
            'y proyectos finalizados (cerrado) para el semillero indicado.'
        ),
        manual_parameters=[
            openapi.Parameter(
                'semillero',
                openapi.IN_QUERY,
                description='ID del semillero.',
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description='Indicadores del semillero',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'proyectos_activos': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'proyectos_finalizados': openapi.Schema(type=openapi.TYPE_INTEGER),
                            },
                        ),
                    },
                ),
            ),
            400: 'semillero es requerido',
            403: 'Sin permiso para este semillero',
        },
        tags=['Dashboard'],
    )
    def get(self, request):
        if getattr(self, 'swagger_fake_view', False):
            return Response({'success': True, 'data': {
                'proyectos_activos': 0,
                'proyectos_finalizados': 0,
            }})

        user = request.user
        semillero_id = request.query_params.get('semillero')

        if not semillero_id:
            return Response(
                {'success': False, 'error': 'semillero es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            semillero_id = int(semillero_id)
        except ValueError:
            return Response(
                {'success': False, 'error': 'semillero debe ser un entero.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not _semillero_visible_para(user, semillero_id):
            return Response(
                {'success': False, 'error': 'No tienes permiso para consultar este semillero.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        proyectos_activos = (
            Proyecto.objects
            .filter(
                semilleros__id=semillero_id,
                estado__in=[
                    Proyecto.EstadoChoices.EN_EJECUCION,
                    Proyecto.EstadoChoices.EN_RESULTADOS,
                ],
            )
            .distinct()
            .count()
        )

        proyectos_finalizados = (
            Proyecto.objects
            .filter(semilleros__id=semillero_id, estado=Proyecto.EstadoChoices.CERRADO)
            .distinct()
            .count()
        )

        return Response(
            {
                'success': True,
                'data': {
                    'proyectos_activos': proyectos_activos,
                    'proyectos_finalizados': proyectos_finalizados,
                },
            },
            status=status.HTTP_200_OK,
        )