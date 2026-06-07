from django.utils.decorators import method_decorator
from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.sigesi.models import ProgramaAcademico
from apps.sigesi.serializers.core.programa_academico_serializer import (
    ProgramaAcademicoSerializer,
    ProgramaAcademicoCreateUpdateSerializer,
)
from apps.sigesi.decorators.permissions import AdminOrReadOnlyPermission


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_summary='Listar programas académicos',
    responses={200: ProgramaAcademicoSerializer(many=True)},
    tags=['Programas Académicos'],
))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(
    operation_summary='Consultar detalle de programa académico',
    responses={200: ProgramaAcademicoSerializer, 404: 'Programa no encontrado'},
    tags=['Programas Académicos'],
))
@method_decorator(name='destroy', decorator=swagger_auto_schema(
    operation_summary='Eliminar programa académico (admin)',
    responses={
        204: openapi.Response('Programa eliminado correctamente'),
        403: openapi.Response('Solo el administrador puede eliminar programas'),
        404: openapi.Response('Programa no encontrado'),
    },
    tags=['Programas Académicos'],
))
class ProgramaAcademicoViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para ProgramaAcademico.

    - Lectura (list/retrieve): cualquier usuario autenticado.
    - Escritura (create/update/partial_update/destroy): solo Administrador.
    """

    queryset = ProgramaAcademico.objects.all().order_by('nombre')
    permission_classes = [AdminOrReadOnlyPermission]

    search_fields = ['nombre', 'codigo', 'facultad']
    ordering_fields = ['nombre', 'codigo', 'facultad', 'created_at']
    ordering = ['nombre']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ProgramaAcademicoCreateUpdateSerializer
        return ProgramaAcademicoSerializer

    @swagger_auto_schema(
        operation_summary='Crear programa académico (admin)',
        request_body=ProgramaAcademicoCreateUpdateSerializer,
        responses={
            201: ProgramaAcademicoSerializer,
            400: openapi.Response('Errores de validación'),
            403: openapi.Response('Solo el administrador puede crear programas'),
        },
        tags=['Programas Académicos'],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            ProgramaAcademicoSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Actualizar programa académico (admin)',
        request_body=ProgramaAcademicoCreateUpdateSerializer,
        responses={
            200: ProgramaAcademicoSerializer,
            400: 'Errores de validación',
            403: 'Solo el administrador puede modificar programas',
            404: 'Programa no encontrado',
        },
        tags=['Programas Académicos'],
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.pop('partial', False)
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(ProgramaAcademicoSerializer(instance).data)

    @swagger_auto_schema(
        operation_summary='Actualizar programa académico (parcial, admin)',
        request_body=ProgramaAcademicoCreateUpdateSerializer,
        responses={
            200: ProgramaAcademicoSerializer,
            400: 'Errores de validación',
            403: 'Solo el administrador puede modificar programas',
            404: 'Programa no encontrado',
        },
        tags=['Programas Académicos'],
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
