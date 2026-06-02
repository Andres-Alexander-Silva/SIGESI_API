import os

from django.http import FileResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from apps.sigesi.models import Semillero, User
from apps.sigesi.serializers.core.semillero_serializer import (
    SemilleroListSerializer,
    SemilleroCreateUpdateSerializer,
    SemilleroAvalSerializer,
)
from apps.sigesi.decorators.permissions import SemilleroRolePermission


class SemilleroViewSet(viewsets.ModelViewSet):
    """
    ViewSet CRUD para la gestión de Semilleros.
    Integra control de acceso por roles y eliminación lógica segura.
    """
    queryset = Semillero.objects.all().order_by('nombre')
    permission_classes = [SemilleroRolePermission]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SemilleroCreateUpdateSerializer
        return SemilleroListSerializer

    @swagger_auto_schema(
        operation_summary="Listar semilleros",
        operation_description="Retorna la lista de todos los semilleros registrados.",
        responses={200: SemilleroListSerializer(many=True)},
        tags=['Semilleros']
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Consultar detalle de semillero",
        operation_description="Retorna la información detallada de un semillero.",
        responses={200: SemilleroListSerializer, 404: "Semillero no encontrado"},
        tags=['Semilleros']
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Crear semillero",
        operation_description="Crea un nuevo semillero validando el grupo asociado.",
        request_body=SemilleroCreateUpdateSerializer,
        responses={
            201: SemilleroListSerializer,
            400: openapi.Response("Errores de validación"),
            403: openapi.Response("No tiene permisos (ej. Director de grupo asignando a otro grupo)")
        },
        tags=['Semilleros']
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        semillero = serializer.save()
        return Response(
            {'message': 'Semillero creado con éxito', 'data': SemilleroListSerializer(semillero).data},
            status=status.HTTP_201_CREATED
        )

    @swagger_auto_schema(
        operation_summary="Actualizar semillero",
        operation_description="Actualiza la información del semillero.",
        request_body=SemilleroCreateUpdateSerializer,
        responses={
            200: SemilleroListSerializer,
            400: "Errores de validación",
            403: "No tiene permisos para modificar este semillero",
            404: "Semillero no encontrado"
        },
        tags=['Semilleros']
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
        serializer.is_valid(raise_exception=True)
        semillero = serializer.save()
        return Response(SemilleroListSerializer(semillero).data)

    @swagger_auto_schema(
        operation_summary="Actualizar semillero (parcial)",
        operation_description="Actualiza campos específicos del semillero.",
        request_body=SemilleroCreateUpdateSerializer,
        responses={
            200: SemilleroListSerializer,
            400: "Errores de validación",
            403: "No tiene permisos",
            404: "Semillero no encontrado"
        },
        tags=['Semilleros']
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Eliminar semillero (lógico)",
        operation_description="Cambia el estado del semillero a inactivo. Falla si tiene dependencias asociadas.",
        responses={
            204: openapi.Response("Semillero inactivado correctamente"),
            400: openapi.Response("No se puede eliminar porque tiene dependencias activas"),
            403: openapi.Response("No tiene permisos"),
            404: openapi.Response("Semillero no encontrado")
        },
        tags=['Semilleros']
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Validación de dependencias antes de desactivar
        tiene_proyectos = instance.proyectos.exists()
        tiene_planes = instance.planes_accion.exists() or instance.planes_estrategicos.exists()
        tiene_matriculas = instance.matriculas.filter(estado='activa').exists()
        
        if tiene_proyectos or tiene_planes or tiene_matriculas:
            return Response(
                {"error": "No es posible eliminar el semillero porque tiene proyectos, planes vigentes o estudiantes activos."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Eliminación lógica
        instance.is_active = False
        instance.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        method='get',
        operation_summary='Consultar aval del semillero',
        operation_description='Retorna el estado actual del aval institucional del semillero.',
        responses={200: SemilleroAvalSerializer, 404: 'Semillero no encontrado'},
        tags=['Semilleros'],
    )
    @swagger_auto_schema(
        method='patch',
        operation_summary='Actualizar aval del semillero (admin)',
        operation_description=(
            'Gestiona el aval institucional del semillero. Solo el Administrador '
            'puede modificarlo. Al transicionar a "aprobado" se requieren '
            'tipo_documento y numero_acta, y se registra automáticamente el '
            'usuario y la fecha de aprobación.'
        ),
        request_body=SemilleroAvalSerializer,
        responses={
            200: SemilleroAvalSerializer,
            400: openapi.Response('Errores de validación'),
            403: openapi.Response('Solo el administrador puede gestionar el aval'),
            404: openapi.Response('Semillero no encontrado'),
        },
        tags=['Semilleros'],
    )
    @action(
        detail=True,
        methods=['get', 'patch'],
        url_path='aval',
        parser_classes=[MultiPartParser, FormParser],
    )
    def aval(self, request, pk=None):
        semillero = self.get_object()

        if request.method == 'GET':
            return Response(SemilleroAvalSerializer(semillero).data)

        user = request.user
        if not user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return Response(
                {'error': 'Solo el administrador puede gestionar el aval.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = SemilleroAvalSerializer(semillero, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        going_aprobado = (
            serializer.validated_data.get('estado_aval')
            == Semillero.EstadoAvalChoices.APROBADO
        )
        was_aprobado = semillero.estado_aval == Semillero.EstadoAvalChoices.APROBADO

        # Limpieza de archivo anterior para evitar archivos huérfanos
        nuevo_archivo = serializer.validated_data.get('archivo_aval')
        if nuevo_archivo and semillero.archivo_aval:
            semillero.archivo_aval.delete(save=False)

        serializer.save()

        if going_aprobado and not was_aprobado:
            semillero.refresh_from_db()
            semillero.usuario_aprobacion = user
            if not semillero.fecha_aprobacion:
                semillero.fecha_aprobacion = timezone.now().date()
            semillero.save(update_fields=['usuario_aprobacion', 'fecha_aprobacion'])

        return Response(SemilleroAvalSerializer(semillero).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='get',
        operation_summary='Descargar archivo del aval',
        operation_description=(
            'Descarga el archivo del aval institucional (archivo_aval) del semillero '
            'como adjunto. Retorna 404 si el semillero no tiene archivo de aval cargado.'
        ),
        responses={
            200: openapi.Response('Archivo del aval', schema=openapi.Schema(type=openapi.TYPE_FILE)),
            404: openapi.Response('El semillero no tiene archivo de aval'),
        },
        tags=['Semilleros'],
    )
    @action(detail=True, methods=['get'], url_path='aval/download')
    def aval_download(self, request, pk=None):
        semillero = self.get_object()

        if not semillero.archivo_aval:
            return Response(
                {'error': 'El semillero no tiene un archivo de aval cargado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        nombre_archivo = os.path.basename(semillero.archivo_aval.name)
        return FileResponse(
            semillero.archivo_aval.open('rb'),
            as_attachment=True,
            filename=nombre_archivo,
        )
