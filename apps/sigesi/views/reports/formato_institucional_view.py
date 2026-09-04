from rest_framework import viewsets

from apps.sigesi.models import FormatoInstitucional, User
from apps.sigesi.serializers.reports.formato_institucional_serializer import (
    FormatoInstitucionalSerializer,
)
from apps.sigesi.decorators.permissions import FormatoInstitucionalPermission
from apps.sigesi.utils.download import ArchiveDownloadMixin, ArchiveUploadMixin


class FormatoInstitucionalViewSet(ArchiveDownloadMixin, ArchiveUploadMixin, viewsets.ModelViewSet):
    """CRUD del repositorio de formatos institucionales (HU-021, fase F4).

    - Administrador: alta, edición, reemplazo de archivo y retiro de formatos.
    - Director de Semillero: solo consulta/descarga de los formatos activos.
    """
    swagger_tags = ['Formatos Institucionales']
    queryset = FormatoInstitucional.objects.all()
    serializer_class = FormatoInstitucionalSerializer
    upload_serializer_class = FormatoInstitucionalSerializer
    permission_classes = [FormatoInstitucionalPermission]
    lookup_field = 'slug'
    filterset_fields = ['categoria', 'tipo_vinculacion', 'estado']
    search_fields = ['nombre', 'descripcion']
    ordering_fields = ['categoria', 'nombre', 'updated_at']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return qs
        # Director de Semillero: solo formatos activos.
        return qs.filter(estado=True)
