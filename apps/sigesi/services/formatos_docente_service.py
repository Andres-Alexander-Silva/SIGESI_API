"""Servicio de renderizado de formatos institucionales para directores de semillero.

Construye el contexto de datos de un usuario (según su alcance de director de
semillero) e inyecta esos datos en las plantillas ``.docx`` mediante ``docxtpl``
(marcadores Jinja ``{{ variable }}``).

El catálogo de variables (claves del contexto) es el contrato que deben respetar
quienes editan las plantillas en Word. Una plantilla **sin** marcadores se
renderiza sin cambios, por lo que el servicio es seguro aun antes de que todas
las plantillas hayan sido preparadas.
"""
from io import BytesIO

from django.utils import timezone
from docxtpl import DocxTemplate

from apps.sigesi.models import Semillero


def construir_contexto_formato(usuario):
    """Construye el contexto de datos para inyectar en un formato docente.

    A partir de ``usuario`` (típicamente un director de semillero) resuelve su
    semillero principal —el más reciente que dirige y está activo— y, a través de
    él, su grupo de investigación, programa académico y líneas. Todas las claves
    del catálogo están siempre presentes (cadena vacía cuando no hay dato) para
    que Jinja nunca encuentre una variable indefinida al renderizar.

    :param usuario: instancia de ``User`` cuyos datos se inyectarán.
    :return: ``dict`` con las variables del catálogo de formatos.
    """
    semillero = (
        Semillero.objects
        .filter(director=usuario, is_active=True)
        .select_related('grupo_investigacion', 'grupo_investigacion__programa_academico')
        .prefetch_related('lineas_investigacion')
        .order_by('-created_at')
        .first()
    )

    grupo = semillero.grupo_investigacion if semillero else None
    # El programa sale del grupo del semillero; si no hay, se usa el del usuario.
    programa = (
        getattr(grupo, 'programa_academico', None)
        or getattr(usuario, 'programa_academico', None)
    )

    if semillero:
        lineas = ', '.join(
            linea.nombre for linea in semillero.lineas_investigacion.all()
        )
    else:
        lineas = ''

    return {
        # Datos del director
        'director_nombre': usuario.get_full_name() or '',
        'director_cedula': usuario.cedula or '',
        'director_tipo_vinculacion': (
            usuario.get_tipo_vinculacion_display() if usuario.tipo_vinculacion else ''
        ),
        'director_correo': usuario.correo_personal or usuario.email or '',
        'director_telefono': usuario.telefono or '',
        # Datos del semillero
        'semillero_nombre': semillero.nombre if semillero else '',
        'semillero_codigo': semillero.codigo if semillero else '',
        'semillero_objetivo': semillero.objetivo if semillero else '',
        'semillero_lineas': lineas,
        # Datos del grupo de investigación
        'grupo_nombre': grupo.nombre if grupo else '',
        'grupo_codigo': grupo.codigo if grupo else '',
        # Datos del programa académico
        'programa_nombre': programa.nombre if programa else '',
        'programa_facultad': programa.facultad if programa else '',
        # Fecha de generación
        'fecha_actual': timezone.now().strftime('%d/%m/%Y'),
    }


def render_formato_docente(abs_path, contexto):
    """Renderiza la plantilla ``.docx`` en ``abs_path`` con ``contexto``.

    Usa ``docxtpl`` para sustituir los marcadores Jinja ``{{ variable }}`` de la
    plantilla por los valores del contexto. Si la plantilla no contiene
    marcadores, se devuelve intacta.

    :param abs_path: ruta absoluta de la plantilla ``.docx``.
    :param contexto: ``dict`` de variables (ver :func:`construir_contexto_formato`).
    :return: ``BytesIO`` posicionado al inicio con el documento renderizado.
    """
    tpl = DocxTemplate(abs_path)
    tpl.render(contexto)
    buffer = BytesIO()
    tpl.save(buffer)
    buffer.seek(0)
    return buffer
