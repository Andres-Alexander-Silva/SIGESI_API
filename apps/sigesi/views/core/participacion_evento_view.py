from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import ParticipacionEvento, User
from apps.sigesi.serializers.core.participacion_evento_serializer import (
    ParticipacionEventoListSerializer,
    ParticipacionEventoCreateUpdateSerializer,
)
from apps.sigesi.decorators.permissions import ParticipacionEventoRolePermission
from apps.sigesi.utils.alcance import participantes_en_alcance
from apps.sigesi.utils.download import ArchiveDownloadMixin, validate_upload_file
from apps.sigesi.utils.notifications import (
    notificar_evento_a_usuarios,
    _resolve_recipients_participacion,
)


class ParticipacionEventoViewSet(ArchiveDownloadMixin, viewsets.ModelViewSet):
    """ViewSet CRUD para las participaciones en eventos.

    Control de acceso (ver :class:`ParticipacionEventoRolePermission`):
    - Administrador: CRUD total.
    - Director de Grupo / Director de Semillero / Líder Estudiantil: CRUD sobre
      las participaciones cuyo participante esté en su alcance.
    - Estudiante: solo lectura de sus propias participaciones.

    El alcance por filas lo aplica ``get_queryset``; qué participante puede
    agregarse lo valida el serializer. El certificado se descarga con
    ``GET /{id}/archive/download/`` (mixin) y se sube con la acción
    ``POST /{id}/cargar-certificado/``.
    """

    # Etiqueta de documentación para las acciones sin decorar (mixin de archivo).
    swagger_tags = ['Participaciones en Eventos']
    queryset = (
        ParticipacionEvento.objects.all()
        .select_related('evento', 'participante', 'produccion')
    )
    permission_classes = [ParticipacionEventoRolePermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ['evento', 'participante', 'tipo_participacion']
    archive_field = 'certificado'

    def get_serializer_class(self):
        """Usa el serializador de escritura en create/update y el de lectura en el resto."""
        if self.action in ['create', 'update', 'partial_update']:
            return ParticipacionEventoCreateUpdateSerializer
        return ParticipacionEventoListSerializer

    def get_queryset(self):
        """Filtra las participaciones según el rol del usuario autenticado."""
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_authenticated:
            return queryset.none()

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return queryset

        # El resto de roles ve solo las participaciones de los participantes a su
        # alcance (que para el estudiante son únicamente las suyas).
        return queryset.filter(
            participante__in=participantes_en_alcance(user)).distinct()

    @swagger_auto_schema(
        operation_summary='Listar participaciones en eventos',
        manual_parameters=[
            openapi.Parameter('evento', openapi.IN_QUERY, description='Filtrar por ID de evento.',
                              type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('participante', openapi.IN_QUERY, description='Filtrar por ID de participante.',
                              type=openapi.TYPE_INTEGER, required=False),
        ],
        responses={200: ParticipacionEventoListSerializer(many=True)},
        tags=['Participaciones en Eventos'],
    )
    def list(self, request, *args, **kwargs):
        """Lista las participaciones visibles para el usuario."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Consultar detalle de participación',
        responses={200: ParticipacionEventoListSerializer, 404: 'Participación no encontrada'},
        tags=['Participaciones en Eventos'],
    )
    def retrieve(self, request, *args, **kwargs):
        """Devuelve el detalle de una participación en evento."""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Registrar participación en evento',
        request_body=ParticipacionEventoCreateUpdateSerializer,
        responses={
            201: ParticipacionEventoListSerializer,
            400: openapi.Response('Errores de validación / participante fuera de alcance'),
            403: openapi.Response('No tiene permisos'),
        },
        tags=['Participaciones en Eventos'],
    )
    def create(self, request, *args, **kwargs):
        """Registra una participación y notifica al participante."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        participacion = serializer.save()
        self._emitir_a_participante(
            participacion,
            tipo='participacion_creada',
            titulo='Fuiste registrado en un evento',
            mensaje=(
                f'Has sido registrado como "{participacion.get_tipo_participacion_display()}" '
                f'en el evento "{participacion.evento.nombre}".'
            ),
            actor=request.user,
        )
        return Response(
            {
                'message': 'Participación registrada con éxito',
                'data': ParticipacionEventoListSerializer(participacion).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Actualizar participación en evento',
        request_body=ParticipacionEventoCreateUpdateSerializer,
        responses={200: ParticipacionEventoListSerializer, 400: 'Errores de validación',
                   403: 'No tiene permisos', 404: 'Participación no encontrada'},
        tags=['Participaciones en Eventos'],
    )
    def update(self, request, *args, **kwargs):
        """Actualiza por completo una participación; notifica al participante."""
        response = super().update(request, *args, **kwargs)
        obj = self.get_object()
        self._emitir_a_participante(
            obj,
            tipo='participacion_actualizada',
            titulo='Tu participación en el evento fue actualizada',
            mensaje=(
                f'Tu participación en el evento "{obj.evento.nombre}" fue '
                f'actualizada.'
            ),
            actor=request.user,
        )
        return response

    @swagger_auto_schema(
        operation_summary='Actualizar participación en evento (parcial)',
        request_body=ParticipacionEventoCreateUpdateSerializer,
        responses={200: ParticipacionEventoListSerializer, 400: 'Errores de validación',
                   403: 'No tiene permisos', 404: 'Participación no encontrada'},
        tags=['Participaciones en Eventos'],
    )
    def partial_update(self, request, *args, **kwargs):
        """Actualiza parcialmente una participación; notifica al participante."""
        response = super().partial_update(request, *args, **kwargs)
        obj = self.get_object()
        self._emitir_a_participante(
            obj,
            tipo='participacion_actualizada',
            titulo='Tu participación en el evento fue actualizada',
            mensaje=(
                f'Tu participación en el evento "{obj.evento.nombre}" fue '
                f'actualizada.'
            ),
            actor=request.user,
        )
        return response

    @swagger_auto_schema(
        operation_summary='Eliminar participación en evento',
        responses={204: openapi.Response('Participación eliminada correctamente'),
                   403: openapi.Response('No tiene permisos'),
                   404: openapi.Response('Participación no encontrada')},
        tags=['Participaciones en Eventos'],
    )
    def destroy(self, request, *args, **kwargs):
        """Elimina una participación en evento; notifica al participante."""
        obj = self.get_object()
        snapshot = obj
        response = super().destroy(request, *args, **kwargs)
        # El objeto ya no existe en DB; emitimos pasando la snapshot.
        notificar_evento_a_usuarios(
            _resolve_recipients_participacion(snapshot).exclude(
                pk=request.user.pk),
            tipo='participacion_actualizada',
            titulo='Tu participación en el evento fue eliminada',
            mensaje=(
                f'Tu participación en el evento "{snapshot.evento.nombre}" '
                f'fue eliminada.'
            ),
            target=None,
        )
        return response

    @swagger_auto_schema(
        method='post',
        operation_summary='Cargar certificado de la participación',
        operation_description=(
            'Sube o reemplaza el certificado (campo multipart `certificado`) de '
            'esta participación. Extensiones permitidas: .pdf/.jpg/.jpeg/.png/'
            '.docx/.xlsx; máximo 5 MB. Pasa por el control de acceso por fila.'
        ),
        manual_parameters=[
            openapi.Parameter('certificado', openapi.IN_FORM,
                              description='Archivo del certificado.',
                              type=openapi.TYPE_FILE, required=True),
        ],
        responses={
            200: ParticipacionEventoListSerializer,
            400: openapi.Response('Archivo faltante o inválido'),
            403: openapi.Response('No tiene permisos'),
            404: openapi.Response('Participación no encontrada'),
        },
        tags=['Participaciones en Eventos'],
    )
    @action(detail=True, methods=['post'], url_path='cargar-certificado',
            parser_classes=[MultiPartParser, FormParser])
    def cargar_certificado(self, request, *args, **kwargs):
        """Sube/reemplaza el certificado de esta participación (campo ``certificado``).

        Enruta por ``get_object()``, de modo que respeta el filtro de
        ``get_queryset`` y ``has_object_permission`` (solo un actor con alcance
        sobre el participante puede subir su certificado).
        """
        obj = self.get_object()
        archivo = request.FILES.get('certificado') or request.FILES.get('file')
        if not archivo:
            return Response(
                {'message': 'Debe adjuntar el archivo en el campo "certificado".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        validate_upload_file(archivo)

        anterior = obj.certificado
        obj.certificado = archivo
        obj.save(update_fields=['certificado', 'updated_at'])
        if anterior and anterior.name and anterior.name != obj.certificado.name:
            anterior.delete(save=False)

        # Notifica al participante de que su certificado fue cargado/reemplazado.
        self._emitir_a_participante(
            obj,
            tipo='participacion_actualizada',
            titulo='Tu certificado fue cargado',
            mensaje=(
                f'Se cargó el certificado de tu participación en el evento '
                f'"{obj.evento.nombre}".'
            ),
            actor=request.user,
        )

        return Response(
            ParticipacionEventoListSerializer(obj).data,
            status=status.HTTP_200_OK,
        )

    def _emitir_a_participante(self, obj, *, tipo, titulo, mensaje, actor):
        """Helper: notifica al ``participante`` de ``obj`` (excluyendo al actor)."""
        destinatarios = _resolve_recipients_participacion(obj).exclude(
            pk=actor.pk)
        if not destinatarios.exists():
            return
        notificar_evento_a_usuarios(
            destinatarios,
            tipo=tipo, titulo=titulo, mensaje=mensaje, target=obj)
