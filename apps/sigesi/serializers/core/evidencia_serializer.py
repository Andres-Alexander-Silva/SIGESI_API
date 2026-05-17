import os
from rest_framework import serializers
from apps.sigesi.models import Evidencia, Actividad
from apps.sigesi.utils.aval import validar_semilleros_avalados
from django.core.exceptions import ValidationError

class EvidenciaSerializer(serializers.ModelSerializer):
    proyecto_id = serializers.IntegerField(source='actividad.proyecto.id', read_only=True)
    subido_por_nombre = serializers.SerializerMethodField(read_only=True)
    
    # Virtual field to accept "proyecto" if needed by frontend, but we enforce "actividad"
    # Actually, let's keep it strictly mapped to Evidencia fields and explain it.
    
    class Meta:
        model = Evidencia
        fields = [
            'id', 'actividad', 'proyecto_id', 'tipo', 'titulo', 
            'descripcion', 'archivo', 'subido_por', 'subido_por_nombre', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['subido_por', 'created_at', 'updated_at']

    def get_subido_por_nombre(self, obj):
        if obj.subido_por:
            return f"{obj.subido_por.first_name} {obj.subido_por.last_name}".strip() or obj.subido_por.email
        return None

    def validate_archivo(self, value):
        if not value:
            return value
            
        # Validate extension
        ext = os.path.splitext(value.name)[1].lower()
        valid_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.docx']
        if ext not in valid_extensions:
            raise serializers.ValidationError(f"Tipo de archivo no permitido. Extensiones válidas: {', '.join(valid_extensions)}")
            
        # Validate size (5MB)
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("El archivo no puede superar los 5MB.")
            
        return value

    def validate(self, data):
        # Description is required (though the model says blank=True, HU says required)
        if not data.get('descripcion') and not self.instance:
             # Wait, model says blank=True, but HU says 'La descripción es obligatoria'
             pass # Will check below
             
        if 'descripcion' in data and not data['descripcion'].strip():
             raise serializers.ValidationError({"descripcion": "La descripción es obligatoria."})
             
        if not self.instance and not data.get('descripcion'):
             raise serializers.ValidationError({"descripcion": "La descripción es obligatoria."})

        # Aval gate: la actividad debe estar en un proyecto cuyos semilleros estén avalados.
        actividad = data.get('actividad') or (self.instance.actividad if self.instance else None)
        if actividad and actividad.proyecto:
            request = self.context.get('request')
            user = request.user if request else None
            validar_semilleros_avalados(
                list(actividad.proyecto.semilleros.all()), user, field_name='actividad'
            )

        return data
