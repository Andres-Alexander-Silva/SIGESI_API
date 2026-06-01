"""Endpoints de descarga de formatos institucionales para directores de semillero.

Dos APIView, ambas restringidas a Administrador y Director de Semillero por
``FormatosDocentePermission``:

- ``FormulariosDocenteBulkView`` — entrega el paquete .zip de formatos que le
  corresponde a un usuario según su ``tipo_vinculacion`` (catedrático o planta).
- ``FormularioDocenteDetailView`` — entrega un formato individual por su slug.

Todos los archivos viven bajo ``MEDIA_ROOT/formatos/``. Los .zip se asumen ya
construidos en disco; estos endpoints solo los sirven como descarga.
"""
import os

from django.conf import settings
from django.http import FileResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import User
from apps.sigesi.decorators.permissions import FormatosDocentePermission


# Carpeta raíz de los formatos dentro de MEDIA_ROOT.
FORMATOS_ROOT = os.path.join(settings.MEDIA_ROOT, 'formatos')

# slug (insensible a mayúsculas) -> ruta relativa dentro de MEDIA_ROOT/formatos/.
FORMATOS_DOCENTE = {
    'plan-accion-semillero': 'planeacion/FO-IN-19 PLAN DE ACCION SEMILLEROS INV V2.docx',
    'plan-accion-grupo': 'planeacion/FO-IN-17 PLAN DE ACCION GRUPOS INV V2.docx',
    'gestion-semillero': 'gestion/FO-IN-14 INFORME GESTION SEM INV V2.docx',
    'solicitud-horas-directores': 'administrativos_y_academicos/FO-IN-05  SOL HORAS INVESTIGACION DIR SEMILLEROS V2.docx',
    'control-cumplimiento-produccion': 'administrativos_y_academicos/FO-IN-08 CON CUMP PROD - GRUP O SEM V1.docx',
    'informe-mensual': 'mensual/FORMATO INFORME MENSUAL SEMILLERO 0X - II SEM 2024.docx',
}

# tipo_vinculacion -> nombre del paquete .zip correspondiente.
TIPO_VINCULACION_ZIP = {
    User.TipoVinculacionChoices.CATEDRATICO: 'formatos_catedratico.zip',
    User.TipoVinculacionChoices.PLANTA: 'formatos_planta.zip',
    User.RolChoices.ADMINISTRADOR: 'formatos_catedratico.zip',
}


def _safe_media_path(rel_path):
    """Resuelve ``rel_path`` dentro de ``FORMATOS_ROOT`` de forma segura.

    Une ``rel_path`` a la carpeta de formatos y verifica que la ruta resultante
    siga contenida en ella (defensa frente a recorridos ``../``). Devuelve la
    ruta absoluta si el archivo existe y está dentro de la carpeta; en caso
    contrario devuelve ``None``.
    """
    root = os.path.realpath(FORMATOS_ROOT)
    abs_path = os.path.realpath(os.path.join(root, rel_path))
    if os.path.commonpath([root, abs_path]) != root:
        return None
    if not os.path.isfile(abs_path):
        return None
    return abs_path


def _file_response(abs_path):
    """Construye un ``FileResponse`` de descarga adjunta para la ruta dada."""
    return FileResponse(
        open(abs_path, 'rb'),
        as_attachment=True,
        filename=os.path.basename(abs_path),
    )


class FormulariosDocenteBulkView(APIView):
    """Descarga el paquete .zip de formatos según el ``tipo_vinculacion`` del usuario."""

    permission_classes = [FormatosDocentePermission]

    @swagger_auto_schema(
        operation_summary='Descargar paquete de formatos del director de semillero',
        operation_description=(
            'Devuelve el archivo .zip de formatos institucionales del usuario indicado. '
            'Para un director de semillero depende de su tipo de vinculación: '
            '`formatos_catedratico.zip` (catedrático) o `formatos_planta.zip` (planta). '
            'Para un administrador entrega el paquete de administrador. El usuario debe '
            'ser administrador, o director de semillero con tipo de vinculación asignado.'
        ),
        manual_parameters=[
            openapi.Parameter(
                'user', openapi.IN_QUERY,
                description='ID del usuario (administrador o director de semillero) cuyos formatos se descargan.',
                type=openapi.TYPE_INTEGER, required=True,
            ),
        ],
        responses={
            200: openapi.Response('Paquete .zip de formatos (descarga adjunta)'),
            400: openapi.Response('Parámetro inválido, usuario sin tipo de vinculación o sin rol válido'),
            403: openapi.Response('No tiene permisos'),
            404: openapi.Response('Usuario o archivo no encontrado'),
        },
        tags=['Formatos Docente'],
    )
    def get(self, request):
        """Resuelve y entrega el .zip de formatos del usuario indicado por ``?user=``."""
        raw_user = request.query_params.get('user')
        if raw_user is None or raw_user == '':
            return Response(
                {'message': 'Debe indicar el parámetro de consulta "user".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user_id = int(raw_user)
        except (TypeError, ValueError):
            return Response(
                {'message': 'El parámetro "user" debe ser un número entero.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            usuario = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'message': 'El usuario especificado no existe.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        es_admin = usuario.tiene_rol(User.RolChoices.ADMINISTRADOR)
        es_director = usuario.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO)

        if not es_admin and not es_director:
            return Response(
                {'message': 'El usuario no es director de semillero ni administrador.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # El administrador descarga el paquete de administrador; el director de
        # semillero, el que corresponde a su tipo de vinculación.
        if es_admin:
            zip_name = TIPO_VINCULACION_ZIP.get(User.RolChoices.ADMINISTRADOR)
        else:
            if not usuario.tipo_vinculacion:
                return Response(
                    {'message': 'El usuario no tiene tipo de vinculación asignado.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            zip_name = TIPO_VINCULACION_ZIP.get(usuario.tipo_vinculacion)

        if zip_name is None:
            return Response(
                {'message': 'El tipo de vinculación del usuario no tiene un paquete de formatos asociado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        abs_path = _safe_media_path(zip_name)
        if abs_path is None:
            return Response(
                {'message': 'El paquete de formatos no se encuentra disponible.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return _file_response(abs_path)


class FormularioDocenteDetailView(APIView):
    """Descarga un formato institucional individual por su slug."""

    permission_classes = [FormatosDocentePermission]

    @swagger_auto_schema(
        operation_summary='Descargar un formato individual',
        operation_description=(
            'Devuelve un formato individual por su nombre (slug), recibido como '
            'parámetro de consulta `form_name`. Valores válidos: `plan-accion-semillero`, '
            '`plan-accion-grupo`, `gestion-semillero`, `solicitud-horas-directores`, '
            '`control-cumplimiento-produccion`, `informe-mensual`.'
        ),
        manual_parameters=[
            openapi.Parameter(
                'form_name', openapi.IN_QUERY,
                description='Slug del formato a descargar (insensible a mayúsculas).',
                type=openapi.TYPE_STRING, required=True,
                enum=list(FORMATOS_DOCENTE.keys()),
            ),
        ],
        responses={
            200: openapi.Response('Formato solicitado (descarga adjunta)'),
            400: openapi.Response('Falta el parámetro form_name'),
            403: openapi.Response('No tiene permisos'),
            404: openapi.Response('Formato no encontrado'),
        },
        tags=['Formatos Docente'],
    )
    def get(self, request):
        """Resuelve y entrega el formato cuyo slug llega en ``?form_name=`` (insensible a mayúsculas)."""
        form_name = request.query_params.get('form_name')
        if not form_name:
            return Response(
                {'message': 'Debe indicar el parámetro de consulta "form_name".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rel_path = FORMATOS_DOCENTE.get(form_name.lower())
        if rel_path is None:
            return Response(
                {'message': 'Formulario no encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        abs_path = _safe_media_path(rel_path)
        if abs_path is None:
            return Response(
                {'message': 'El formato no se encuentra disponible.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return _file_response(abs_path)
