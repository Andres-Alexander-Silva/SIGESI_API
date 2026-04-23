from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from apps.sigesi.models import Semillero
from apps.sigesi.serializers.config.semillero_serializer import (
    SemilleroListSerializer,
    SemilleroCreateUpdateSerializer
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
        tags=["Semilleros"]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Consultar detalle de semillero",
        operation_description="Retorna la información detallada de un semillero.",
        responses={200: SemilleroListSerializer, 404: "Semillero no encontrado"},
        tags=["Semilleros"]
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
        tags=["Semilleros"]
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
        tags=["Semilleros"]
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
        tags=["Semilleros"]
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
        tags=["Semilleros"]
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
