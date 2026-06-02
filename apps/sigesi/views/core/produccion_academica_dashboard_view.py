"""Dashboard de producción académica por línea de investigación."""
from django.db.models import Count, F, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import (
    User,
    Semillero,
    ProduccionAcademica,
    MatriculaSemillero,
)


class ProduccionAcademicaDashboardPermission(IsAuthenticated):
    """Permiso para el dashboard de producción académica.

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


def _parse_periodo(periodo):
    """Convierte '2026-1' → (2026, [1,2,3,4,5,6]), '2026-2' → (2026, [7,8,9,10,11,12]).

    Retorna (year, meses) o (None, None) si el formato es inválido.
    """
    if not periodo:
        return None, None
    parts = periodo.split('-')
    if len(parts) != 2:
        return None, None
    try:
        year = int(parts[0])
        half = int(parts[1])
    except ValueError:
        return None, None
    if half == 1:
        return year, [1, 2, 3, 4, 5, 6]
    if half == 2:
        return year, [7, 8, 9, 10, 11, 12]
    return None, None


def _semillero_visible_para(user, semillero_id):
    """Verifica si el usuario puede ver datos del semillero dado.

    Returns True para administrador sin restricción;
    para director_grupo y director_semillero valida que el semillero
    pertenezca a su alcance.
    """
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


class ProduccionAcademicaDashboardView(APIView):
    """Indicadores de producción académica agrupados por línea de investigación.

    Filtra por semillero, periodo (semestre de publicación) y cohorte
    (matrícula activa del estudiante en ese periodo). Retorna para cada
    línea: cantidad de autores únicos (participacion) y cantidad de
    producciones académicas.
    """

    permission_classes = [ProduccionAcademicaDashboardPermission]

    @swagger_auto_schema(
        operation_summary='Dashboard de producción académica',
        operation_description=(
            'Retorna para cada línea de investigación asociada al semillero '
            'indicado: el total de autores únicos (participacion) y el total '
            'de producciones académicas, filtrados por periodo y cohorte.'
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['semillero_id'],
            properties={
                'periodo': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Semestre en formato 'YYYY-1' o 'YYYY-2'. "
                                "Filtra producciones por fecha de publicación.",
                ),
                'semillero_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID del semillero whose datos se consultan.",
                ),
                'cohorte': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Año de cohorte (ej. '2024'). Filtra los autores "
                                "que tengan una matrícula activa cuyo semestre "
                                "empiece con este valor.",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description='Indicadores por línea de investigación',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'linea_investigacion': openapi.Schema(
                                        type=openapi.TYPE_STRING),
                                    'participacion': openapi.Schema(
                                        type=openapi.TYPE_INTEGER),
                                    'produccion_academica': openapi.Schema(
                                        type=openapi.TYPE_INTEGER),
                                },
                            ),
                        ),
                    },
                ),
            ),
            400: 'Parámetros inválidos',
            403: 'Sin permiso para consultar este semillero',
        },
        tags=['Dashboard'],
    )
    def post(self, request):
        if getattr(self, 'swagger_fake_view', False):
            return Response({'success': True, 'data': []})
        user = request.user
        data = request.data

        semillero_id = data.get('semillero_id')
        periodo = data.get('periodo') or None
        cohorte = data.get('cohorte') or None

        if not semillero_id:
            return Response(
                {'success': False, 'error': 'semillero_id es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar que el semillero_id esté dentro del alcance del usuario
        if not _semillero_visible_para(user, semillero_id):
            return Response(
                {'success': False, 'error': 'No tienes permiso para consultar este semillero.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Construir queryset base de producciones para ese semillero
        producciones_qs = ProduccionAcademica.objects.filter(semillero_id=semillero_id)

        # Filtro por periodo (fecha de publicación)
        if periodo:
            year, meses = _parse_periodo(periodo)
            if year is None:
                return Response(
                    {'success': False, 'error': "periodo debe tener formato 'YYYY-1' o 'YYYY-2'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            producciones_qs = producciones_qs.filter(
                fecha_publicacion__year=year,
                fecha_publicacion__month__in=meses,
            )

        # Filtro por cohorte: autores que tengan matrícula activa en el semillero
        # con semestre que empiece con el valor de cohorte
        if cohorte:
            autores_cohorte = User.objects.filter(
                matriculas_semillero__semestre__startswith=cohorte,
                matriculas_semillero__estado=MatriculaSemillero.EstadoChoices.ACTIVA,
                matriculas_semillero__semillero_id=semillero_id,
            )
            producciones_qs = producciones_qs.filter(autores__in=autores_cohorte)

        # Agregación por línea de investigación
        aggregated = (
            producciones_qs
            .values(linea_fk=F('linea_investigacion'))
            .annotate(
                linea_nombre=F('linea_investigacion__nombre'),
                participacion=Count('autores', distinct=True),
                produccion_academica=Count('id', distinct=True),
            )
            .order_by('linea_nombre')
        )

        result = []
        for row in aggregated:
            result.append({
                'linea_investigacion': row['linea_nombre'] or 'Sin línea asignada',
                'participacion': row['participacion'],
                'produccion_academica': row['produccion_academica'],
            })

        return Response({'success': True, 'data': result}, status=status.HTTP_200_OK)