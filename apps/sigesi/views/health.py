from django.db import connection
from django.db.utils import OperationalError
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status


@swagger_auto_schema(
    method='get',
    operation_summary='Ping de disponibilidad',
    operation_description='Responde "pong" para verificar que el servicio está en línea.',
    tags=['Estado del Servicio'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def ping(request):
    """Endpoint mínimo de disponibilidad (no consulta la base de datos)."""
    return Response({'message': 'pong'}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    operation_summary='Estado de salud del servicio',
    operation_description='Verifica la conectividad con la base de datos; responde 503 si falla.',
    tags=['Estado del Servicio'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    """Comprueba la conexión a la base de datos y reporta el estado del servicio."""
    db_status = 'ok'
    try:
        connection.ensure_connection()
    except OperationalError:
        db_status = 'error'

    http_status = status.HTTP_200_OK if db_status == 'ok' else status.HTTP_503_SERVICE_UNAVAILABLE

    return Response({
        'status': 'ok' if db_status == 'ok' else 'error',
        'database': db_status,
    }, status=http_status)
