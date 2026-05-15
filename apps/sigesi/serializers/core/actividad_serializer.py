from rest_framework import serializers
from apps.sigesi.models import Actividad
from apps.sigesi.utils.aval import validar_semilleros_avalados

class ActividadListSerializer(serializers.ModelSerializer):
    """
    Serializador para listar y ver detalles de Actividad.
    Incluye campos de solo lectura con nombres representativos.
    """
    proyecto_titulo = serializers.CharField(source='proyecto.titulo', read_only=True)
    responsable_nombre = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Actividad
        fields = [
            'id', 'proyecto', 'proyecto_titulo', 'titulo', 'descripcion',
            'responsable', 'responsable_nombre', 'fecha_inicio', 'fecha_fin',
            'estado', 'porcentaje_avance', 'created_at', 'updated_at'
        ]

    def get_responsable_nombre(self, obj):
        if obj.responsable:
            return f"{obj.responsable.first_name} {obj.responsable.last_name}".strip() or obj.responsable.email
        return None


class ActividadCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializador para crear y actualizar Actividad.
    Incluye validaciones de negocio.
    """
    class Meta:
        model = Actividad
        fields = [
            'proyecto', 'titulo', 'descripcion', 'responsable',
            'fecha_inicio', 'fecha_fin', 'estado', 'porcentaje_avance'
        ]

    def validate(self, data):
        """
        Validar que la fecha de inicio no sea posterior a la fecha de fin.
        También validar el porcentaje de avance.
        """
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        
        # En actualizaciones parciales, necesitamos obtener el valor actual si no se proporciona
        if self.instance:
            fecha_inicio = fecha_inicio or self.instance.fecha_inicio
            fecha_fin = fecha_fin or self.instance.fecha_fin

        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise serializers.ValidationError({
                "fecha_fin": "La fecha de fin no puede ser anterior a la fecha de inicio."
            })

        porcentaje_avance = data.get('porcentaje_avance')
        if porcentaje_avance is not None and (porcentaje_avance < 0 or porcentaje_avance > 100):
            raise serializers.ValidationError({
                "porcentaje_avance": "El porcentaje de avance debe estar entre 0 y 100."
            })

        # Aval gate: el proyecto debe enlazar solo semilleros con aval aprobado.
        proyecto = data.get('proyecto') or (self.instance.proyecto if self.instance else None)
        if proyecto:
            request = self.context.get('request')
            user = request.user if request else None
            validar_semilleros_avalados(
                list(proyecto.semilleros.all()), user, field_name='proyecto'
            )

        return data
