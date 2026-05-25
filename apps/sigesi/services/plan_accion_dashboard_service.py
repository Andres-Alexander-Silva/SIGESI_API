"""Agregaciones del dashboard de un Plan de Acción.

Calcula, vía ORM, las métricas que consume el endpoint
``GET /api/v1/core/plan-accion/{id}/dashboard/``.
"""
from django.db.models import Count, F, Q
from django.utils import timezone

from apps.sigesi.models import ActividadCronograma, ObjetivosPlanAccion


def _porcentaje(parte, total):
    """Devuelve el porcentaje de ``parte`` sobre ``total`` (0.0 si ``total`` es 0)."""
    if not total:
        return 0.0
    return round(parte / total * 100, 2)


def _objetivos_por_categoria(plan):
    """Distribución de los objetivos del plan por categoría.

    Retorna el total de objetivos y una entrada por cada categoría de
    :class:`ObjetivosPlanAccion` (las categorías sin objetivos se incluyen con
    cantidad y porcentaje en 0).
    """
    conteos = {
        fila['categoria']: fila['cantidad']
        for fila in plan.objetivos.values('categoria').annotate(cantidad=Count('id'))
    }
    total = sum(conteos.values())

    categorias = [
        {
            'categoria': valor,
            'label': etiqueta,
            'cantidad': conteos.get(valor, 0),
            'porcentaje': _porcentaje(conteos.get(valor, 0), total),
        }
        for valor, etiqueta in ObjetivosPlanAccion.CategoriaChoices.choices
    ]
    return {'total': total, 'categorias': categorias}


def _actividades_por_responsable(base_qs):
    """Actividades asignadas y completadas por responsable.

    Agrupa el queryset de actividades por responsable e incluye un grupo
    ``Sin responsable`` para las actividades sin responsable asignado.
    """
    completada = ActividadCronograma.EstadoChoices.COMPLETADA
    filas = (
        base_qs
        .values('responsable', 'responsable__first_name', 'responsable__last_name')
        .annotate(
            asignadas=Count('id'),
            completadas=Count('id', filter=Q(estado=completada)),
        )
        .order_by('-asignadas')
    )

    resultado = []
    for fila in filas:
        nombre = f"{fila['responsable__first_name'] or ''} {fila['responsable__last_name'] or ''}".strip()
        resultado.append({
            'responsable_id': fila['responsable'],
            'responsable_nombre': nombre if fila['responsable'] else 'Sin responsable',
            'asignadas': fila['asignadas'],
            'completadas': fila['completadas'],
            'porcentaje': _porcentaje(fila['completadas'], fila['asignadas']),
        })
    return resultado


def generar_dashboard(plan):
    """Construye el diccionario de métricas del dashboard del plan de acción.

    :param plan: instancia de :class:`PlanAccion` ya resuelta y autorizada.
    :returns: ``dict`` serializable con la distribución de objetivos por
        categoría, el cumplimiento de actividades, el desglose por responsable
        y la puntualidad (actividades a tiempo vs. atrasadas).

    Una actividad se considera *atrasada* si está completada y su
    ``fecha_fin`` supera ``fecha_fin_estimada``, o si no está completada y su
    ``fecha_fin_estimada`` ya pasó. El resto se cuenta como *a tiempo*.
    """
    completada = ActividadCronograma.EstadoChoices.COMPLETADA
    base_qs = ActividadCronograma.objects.filter(cronograma__plan_accion=plan)

    total_actividades = base_qs.count()
    completadas = base_qs.filter(estado=completada).count()

    hoy = timezone.localdate()
    atrasada_q = (
        Q(estado=completada, fecha_fin__gt=F('fecha_fin_estimada'))
        | (~Q(estado=completada) & Q(fecha_fin_estimada__lt=hoy))
    )
    atrasadas = base_qs.filter(atrasada_q).count()

    return {
        'plan_accion': {
            'id': plan.id,
            'titulo': plan.titulo,
            'semestre': plan.semestre,
            'estado': plan.estado,
        },
        'objetivos_por_categoria': _objetivos_por_categoria(plan),
        'cumplimiento_actividades': {
            'total': total_actividades,
            'completadas': completadas,
            'porcentaje': _porcentaje(completadas, total_actividades),
        },
        'actividades_por_responsable': _actividades_por_responsable(base_qs),
        'puntualidad': {
            'total': total_actividades,
            'a_tiempo': total_actividades - atrasadas,
            'atrasadas': atrasadas,
        },
    }
