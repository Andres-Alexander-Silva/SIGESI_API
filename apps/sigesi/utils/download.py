"""Mixin reutilizable para descargar el archivo de un recurso.

Agrega la acción ``GET /{id}/archive/download/`` a cualquier ModelViewSet cuyo
modelo tenga uno o varios FileField. La descarga:

- hereda los ``permission_classes`` del ViewSet (GET es método seguro);
- pasa por ``get_object()``, por lo que respeta el filtro de ``get_queryset()``
  (control de acceso a nivel de fila sin lógica adicional).
"""
import os

from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class ArchiveDownloadMixin:
    """Configurar en el ViewSet uno de:

        archive_field = 'archivo_cronograma'            # FileField único

        # o, para modelos con varios archivos:
        archive_fields = {'archivo': 'archivo', 'certificado': 'certificado'}
        # se elige con ?field=<alias>; sin el parámetro se usa el primero.
    """
    archive_field = 'archivo'
    archive_fields = None

    def _resolver_campo(self, request):
        if self.archive_fields:
            alias = request.query_params.get('field')
            if alias is None:
                return next(iter(self.archive_fields.values()))
            return self.archive_fields.get(alias)
        return self.archive_field

    @swagger_auto_schema(
        method='get',
        operation_summary='Descargar archivo del registro',
        manual_parameters=[
            openapi.Parameter(
                'field', openapi.IN_QUERY, required=False, type=openapi.TYPE_STRING,
                description='Para registros con varios archivos (ej: archivo | certificado).',
            ),
        ],
        responses={
            200: openapi.Response('Archivo del registro', openapi.Schema(type=openapi.TYPE_FILE)),
            400: openapi.Response('Campo de archivo no válido'),
            404: openapi.Response('El registro no tiene archivo asociado'),
        },
    )
    @action(detail=True, methods=['get'], url_path='archive/download')
    def archive_download(self, request, *args, **kwargs):
        obj = self.get_object()
        field_name = self._resolver_campo(request)
        if not field_name:
            return Response(
                {'error': 'Campo de archivo no válido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        archivo = getattr(obj, field_name, None)
        if not archivo:
            return Response(
                {'error': 'Este registro no tiene un archivo asociado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return FileResponse(
            archivo.open('rb'),
            as_attachment=True,
            filename=os.path.basename(archivo.name),
        )
