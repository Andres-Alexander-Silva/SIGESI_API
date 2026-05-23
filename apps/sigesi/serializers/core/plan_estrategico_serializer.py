from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.sigesi.models import PlanEstrategico, User
from apps.sigesi.serializers.core.semillero_serializer import SemilleroListSerializer


class PlanEstrategicoListSerializer(serializers.ModelSerializer):
    """Serializador para listar y ver el detalle de un PlanEstrategico.

    Embebe la información completa del semillero asociado (solo lectura) en el
    campo ``semillero``, de modo que las respuestas de lectura traen el objeto
    del semillero y no únicamente su id.
    """

    semillero = SemilleroListSerializer(read_only=True)

    class Meta:
        model = PlanEstrategico
        fields = [
            'id', 'semillero', 'titulo', 'anio',
            'objetivos', 'metas', 'indicadores', 'estado',
            'created_at', 'updated_at',
        ]


class PlanEstrategicoCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializador para crear y actualizar un PlanEstrategico.

    Reglas de negocio:

    - Un semillero solo puede tener un plan estratégico por año; la restricción
      ``unique_together = ['semillero', 'anio']`` del modelo genera el
      ``UniqueTogetherValidator`` que devuelve un 400 ante un duplicado.
    - El campo ``estado`` solo puede ser modificado por el Administrador o el
      Director de Grupo. El alcance "Director de Grupo solo sobre su grupo" lo
      garantizan el filtro de queryset y ``has_object_permission`` de la vista;
      aquí solo se valida el rol que intenta cambiar el estado.
    """

    class Meta:
        model = PlanEstrategico
        fields = [
            'semillero', 'titulo', 'anio',
            'objetivos', 'metas', 'indicadores', 'estado',
        ]

    def _es_transicion(self, nuevo_estado):
        """¿``nuevo_estado`` cambia respecto al estado actual de la instancia?"""
        estado_actual = self.instance.estado if self.instance else None
        return nuevo_estado != estado_actual

    def validate(self, data):
        """Restringe el cambio de ``estado`` a Administrador / Director de Grupo."""
        request = self.context.get('request')
        user = request.user if request else None

        nuevo_estado = data.get(
            'estado',
            self.instance.estado if self.instance
            else PlanEstrategico.EstadoChoices.BORRADOR,
        )

        if 'estado' in data and self._es_transicion(nuevo_estado):
            if not (user and user.tiene_alguno_de([
                User.RolChoices.ADMINISTRADOR,
                User.RolChoices.DIRECTOR_GRUPO,
            ])):
                raise PermissionDenied(
                    'Solo el Administrador o el Director de Grupo pueden '
                    'cambiar el estado de un plan estratégico.'
                )

        return data
