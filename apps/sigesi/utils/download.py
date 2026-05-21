"""Mixins reutilizables para descargar y subir el archivo de un recurso.

Agregan a cualquier ModelViewSet cuyo modelo tenga uno o varios FileField:

- ``GET   /{id}/archive/download/`` (ArchiveDownloadMixin)
- ``PATCH /{id}/archive/upload/``   (ArchiveUploadMixin)

Ambas acciones pasan por ``get_object()``, de modo que respetan el filtro de
``get_queryset()`` y ``has_object_permission`` del ViewSet (control de acceso a
nivel de fila sin lógica adicional).
"""
import os

from django.http import FileResponse
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


# Validación uniforme de archivos subidos.
ALLOWED_UPLOAD_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.docx', '.xlsx'}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_upload_file(f):
    """Valida extensión y tamaño; lanza ValidationError (-> 400) si no cumple."""
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise serializers.ValidationError(
            f"Tipo de archivo no permitido. Válidos: "
            f"{', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}."
        )
    if f.size > MAX_UPLOAD_SIZE:
        raise serializers.ValidationError("El archivo no puede superar los 5MB.")


class _ArchiveFieldMixin:
    """Resolución del FileField objetivo (compartida por descarga y subida).

    Configurar en el ViewSet uno de::

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


class ArchiveDownloadMixin(_ArchiveFieldMixin):
    """Agrega ``GET /{id}/archive/download/`` (hereda los permisos del ViewSet)."""

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


class ArchiveUploadMixin(_ArchiveFieldMixin):
    """Agrega ``PATCH /{id}/archive/upload/`` (multipart, campo ``file``).

    Reutiliza el serializer create/update del recurso (declarar
    ``upload_serializer_class``) en modo parcial, conservando así el gate de aval
    y la autorización de una actualización normal. Aplica además la validación
    uniforme de archivo y limpia el archivo anterior al reemplazarlo.
    """
    upload_serializer_class = None

    @swagger_auto_schema(
        method='patch',
        operation_summary='Subir / reemplazar archivo del registro',
        manual_parameters=[
            openapi.Parameter(
                'file', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True,
                description='Archivo a subir (pdf, jpg, png, docx, xlsx; máx 5MB).',
            ),
            openapi.Parameter(
                'field', openapi.IN_QUERY, required=False, type=openapi.TYPE_STRING,
                description='Para registros con varios archivos (ej: archivo | certificado).',
            ),
        ],
        responses={
            200: openapi.Response('Archivo actualizado'),
            400: openapi.Response('Archivo inválido o faltante'),
            403: openapi.Response('Sin permisos para modificar este registro'),
        },
    )
    @action(detail=True, methods=['patch'], url_path='archive/upload',
            parser_classes=[MultiPartParser, FormParser])
    def archive_upload(self, request, *args, **kwargs):
        obj = self.get_object()
        field_name = self._resolver_campo(request)
        if not field_name:
            return Response(
                {'error': 'Campo de archivo no válido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        archivo = request.FILES.get('file')
        if not archivo:
            return Response(
                {'error': 'Debe adjuntar un archivo en el campo "file".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        validate_upload_file(archivo)

        old_file = getattr(obj, field_name, None)
        serializer = self.upload_serializer_class(
            obj, data={field_name: archivo}, partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        new_file = getattr(obj, field_name, None)
        if old_file and new_file and old_file.name != new_file.name:
            old_file.delete(save=False)

        return Response(self.get_serializer(obj).data, status=status.HTTP_200_OK)
