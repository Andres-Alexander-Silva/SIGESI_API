from rest_framework import serializers
from apps.sigesi.models import EvaluacionProyecto, Proyecto
from apps.sigesi.utils.aval import validar_semilleros_avalados

class EvaluacionProyectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluacionProyecto
        fields = [
            'id',
            'proyecto',
            'evaluador',
            'calificacion',
            'estado_proyecto',
            'observaciones',
            'recomendaciones',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'evaluador', 'created_at', 'updated_at']

    def validate_calificacion(self, value):
        if value < 0.0 or value > 5.0:
            raise serializers.ValidationError("La calificación debe estar entre 0.0 y 5.0")
        return value

    def validate_estado_proyecto(self, value):
        if value not in dict(Proyecto.EstadoChoices.choices).keys():
            raise serializers.ValidationError("Estado de proyecto no válido.")
        return value

    def validate_observaciones(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Las observaciones son requeridas y deben tener al menos 10 caracteres.")
        return value

    def validate(self, attrs):
        proyecto = attrs.get('proyecto')
        if not proyecto and self.instance:
            proyecto = self.instance.proyecto

        if not proyecto:
            raise serializers.ValidationError({"proyecto": "El proyecto es requerido."})

        if not proyecto.is_active:
            raise serializers.ValidationError("No se puede evaluar un proyecto inactivo.")

        request = self.context.get('request')
        user = request.user if request else None

        # Aval gate: los semilleros del proyecto deben estar avalados.
        validar_semilleros_avalados(
            list(proyecto.semilleros.all()), user, field_name='proyecto'
        )

        if user:
            if getattr(user, 'rol', None) == 'admin':
                return attrs

            is_director_proyecto = (proyecto.director == user)
            is_director_semillero = proyecto.semilleros.filter(director=user).exists()

            if not (is_director_proyecto or is_director_semillero):
                raise serializers.ValidationError("No tiene relación académica válida para evaluar este proyecto.")

        return attrs
