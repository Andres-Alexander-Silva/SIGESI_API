"""Descarga masiva ("todos mis formatos") de formatos institucionales.

`FormatoInstitucionalViewSet` (formato_institucional_view.py) es el CRUD
completo del repositorio de formatos y ya expone la descarga individual vía
`{slug}/archive/download/`. Este endpoint arma sobre la marcha el .zip "todos
mis formatos" según el tipo de vinculación del usuario, en lugar de servir un
.zip pre-construido en disco que había que regenerar a mano cada vez que
cambiaba un formato (HU-021, fase F4).

La vista `FormularioDocenteDetailView` (descarga individual por slug) y el
diccionario `FORMATOS_DOCENTE` que existían aquí se retiraron: quedaron
totalmente cubiertos por `FormatoInstitucionalViewSet`, y el cliente nunca
llegó a consumirlos (no hay ninguna referencia en SIGESI_CLIENT).
"""
import io
import os
import zipfile

from django.db.models import Q
from django.http import FileResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import FormatoInstitucional, User
from apps.sigesi.decorators.permissions import FormatosDocentePermission


class FormulariosDocenteBulkView(APIView):
    """Descarga en un .zip todos los formatos activos del tipo de vinculación del usuario."""

    permission_classes = [FormatosDocentePermission]

    @swagger_auto_schema(
        operation_summary='Descargar paquete de formatos del director de semillero',
        operation_description=(
            'Arma un .zip con los formatos institucionales activos que aplican al '
            'usuario indicado: los de tipo_vinculacion nulo (aplican a todos) más los '
            'específicos de su tipo de vinculación. El administrador recibe el mismo '
            'conjunto que un catedrático.'
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
            404: openapi.Response('Usuario no encontrado, o sin formatos disponibles'),
        },
        tags=['Formatos Docente'],
    )
    def get(self, request):
        """Resuelve y arma el .zip de formatos del usuario indicado por ``?user=``."""
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

        # El administrador descarga el mismo conjunto que un catedrático; el
        # director de semillero, el que corresponde a su tipo de vinculación.
        if es_admin:
            tipo_vinculacion = User.TipoVinculacionChoices.CATEDRATICO
        else:
            if not usuario.tipo_vinculacion:
                return Response(
                    {'message': 'El usuario no tiene tipo de vinculación asignado.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            tipo_vinculacion = usuario.tipo_vinculacion

        formatos = FormatoInstitucional.objects.filter(estado=True).filter(
            Q(tipo_vinculacion__isnull=True) | Q(tipo_vinculacion=tipo_vinculacion)
        )
        if not formatos.exists():
            return Response(
                {'message': 'No hay formatos disponibles para este tipo de vinculación.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for formato in formatos:
                if not formato.archivo:
                    continue
                nombre_en_zip = os.path.basename(formato.archivo.name)
                with formato.archivo.open('rb') as f:
                    zf.writestr(nombre_en_zip, f.read())
        buffer.seek(0)

        return FileResponse(
            buffer, as_attachment=True, filename=f'formatos_{tipo_vinculacion}.zip',
        )
