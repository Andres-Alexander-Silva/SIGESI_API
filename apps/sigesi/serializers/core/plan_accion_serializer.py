from rest_framework import serializers
from apps.sigesi.models import PlanAccion
from apps.sigesi.utils.aval import validar_semilleros_avalados


class PlanAccionListSerializer(serializers.ModelSerializer):
    """Serializador para listar y ver detalle de un PlanAccion."""

    semillero_nombre = serializers.CharField(source='semillero.nombre', read_only=True)
    aprobado_por_nombre = serializers.CharField(
        source='aprobado_por.get_full_name', read_only=True)

    class Meta:
        model = PlanAccion
        fields = [
            'id', 'semillero', 'semillero_nombre',
            'plan_estrategico', 'titulo', 'semestre',
            'objetivos', 'metas', 'estado',
            'aprobado_por', 'aprobado_por_nombre', 'fecha_aprobacion',
            'created_at', 'updated_at',
        ]


class PlanAccionCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializador para crear y actualizar un PlanAccion.

    Omite deliberadamente ``estado``, ``aprobado_por`` y ``fecha_aprobacion``:
    el estado de aprobación solo se cambia por la acción ``aprobar`` (Admin /
    Director de Grupo), nunca por el CRUD normal.
    """

    class Meta:
        model = PlanAccion
        fields = [
            'semillero', 'plan_estrategico', 'titulo',
            'semestre', 'objetivos', 'metas',
        ]

    def validate(self, data):
        # Aval gate: el semillero del plan debe tener aval aprobado.
        semillero = data.get('semillero') or (
            self.instance.semillero if self.instance else None)
        if semillero:
            request = self.context.get('request')
            user = request.user if request else None
            validar_semilleros_avalados(
                [semillero], user, field_name='semillero'
            )

        return data
