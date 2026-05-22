from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.sigesi.models import PlanAccion, User
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


# Estados que limpian la información de aprobación al fijarse.
ESTADOS_LIMPIA_APROBACION = {
    PlanAccion.EstadoChoices.BORRADOR,
    PlanAccion.EstadoChoices.ENVIADO,
}
# Estados que solo pueden fijarse si el plan ya fue aprobado previamente.
ESTADOS_REQUIEREN_APROBACION = {
    PlanAccion.EstadoChoices.RECHAZADO,
    PlanAccion.EstadoChoices.EN_EJECUCION,
    PlanAccion.EstadoChoices.FINALIZADO,
}


class PlanAccionCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializador para crear y actualizar un PlanAccion.

    ``estado`` es escribible y dispara la lógica de aprobación, igual que la
    acción ``aprobar``:

    - ``aprobado``: solo Admin / Director de Grupo. Fija ``aprobado_por`` al
      usuario de la solicitud y ``fecha_aprobacion`` a la fecha actual.
    - ``borrador`` / ``enviado``: limpia ``aprobado_por`` y ``fecha_aprobacion``.
    - ``rechazado`` / ``en_ejecucion`` / ``finalizado``: solo si el plan fue
      aprobado previamente (``aprobado_por`` no nulo); conservan la información
      de aprobación.

    ``aprobado_por`` y ``fecha_aprobacion`` no son escribibles directamente: los
    gestiona el servidor según ``estado``.
    """

    class Meta:
        model = PlanAccion
        fields = [
            'semillero', 'plan_estrategico', 'titulo',
            'semestre', 'objetivos', 'metas', 'estado',
        ]

    def _es_transicion(self, nuevo_estado):
        """¿``nuevo_estado`` cambia respecto al estado actual de la instancia?"""
        estado_actual = self.instance.estado if self.instance else None
        return nuevo_estado != estado_actual

    def validate(self, data):
        request = self.context.get('request')
        user = request.user if request else None

        # Aval gate: el semillero del plan debe tener aval aprobado.
        semillero = data.get('semillero') or (
            self.instance.semillero if self.instance else None)
        if semillero:
            validar_semilleros_avalados([semillero], user, field_name='semillero')

        # Validación de transición de estado.
        nuevo_estado = data.get(
            'estado',
            self.instance.estado if self.instance else PlanAccion.EstadoChoices.BORRADOR,
        )
        previamente_aprobado = bool(self.instance and self.instance.aprobado_por_id)

        if 'estado' in data and self._es_transicion(nuevo_estado):
            # Aprobar via CRUD: mismo control que la acción /aprobar.
            if nuevo_estado == PlanAccion.EstadoChoices.APROBADO:
                if not (user and user.tiene_alguno_de([
                    User.RolChoices.ADMINISTRADOR,
                    User.RolChoices.DIRECTOR_GRUPO,
                ])):
                    raise PermissionDenied(
                        'Solo el Administrador o el Director de Grupo pueden '
                        'aprobar un plan de acción.'
                    )

            # Estados de ejecución/cierre/rechazo: requieren aprobación previa.
            if nuevo_estado in ESTADOS_REQUIEREN_APROBACION and not previamente_aprobado:
                raise serializers.ValidationError({
                    'estado': 'El plan debe haber sido aprobado previamente '
                              'para pasar a este estado.'
                })

        return data

    def _aplicar_estado(self, validated_data):
        """Resuelve ``aprobado_por``/``fecha_aprobacion`` según el ``estado`` objetivo.

        Solo actúa cuando ``estado`` está presente y representa una transición;
        re-enviar el estado actual (p. ej. un PUT sobre un plan ya aprobado) es
        un no-op y no vuelve a sellar ni borra la aprobación.
        """
        if 'estado' not in validated_data:
            return validated_data

        nuevo_estado = validated_data['estado']
        if not self._es_transicion(nuevo_estado):
            return validated_data

        if nuevo_estado == PlanAccion.EstadoChoices.APROBADO:
            request = self.context.get('request')
            validated_data['aprobado_por'] = request.user if request else None
            validated_data['fecha_aprobacion'] = timezone.now()
        elif nuevo_estado in ESTADOS_LIMPIA_APROBACION:
            validated_data['aprobado_por'] = None
            validated_data['fecha_aprobacion'] = None
        # Estados que requieren aprobación previa: conservan el sello existente.

        return validated_data

    def create(self, validated_data):
        validated_data = self._aplicar_estado(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._aplicar_estado(validated_data)
        return super().update(instance, validated_data)
