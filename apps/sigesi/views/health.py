from django.db import connection
from django.db.utils import OperationalError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET'])
@permission_classes([AllowAny])
def ping(request):
    return Response({'message': 'pong'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
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
