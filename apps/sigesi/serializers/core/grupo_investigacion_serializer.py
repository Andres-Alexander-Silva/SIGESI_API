from rest_framework import serializers
from apps.sigesi.models import GrupoInvestigacion

class GrupoInvestigacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrupoInvestigacion
        fields = [
            'id', 'nombre', 'codigo', 'descripcion', 'fecha_creacion', 
            'programa_academico', 'director', 'lineas_investigacion', 
            'is_active', 'created_at', 'updated_at'
        ]

class GrupoInvestigacionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrupoInvestigacion
        fields = [
            'nombre', 'codigo', 'descripcion', 'fecha_creacion', 
            'programa_academico', 'director', 'lineas_investigacion', 'is_active'
        ]

class GrupoInvestigacionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrupoInvestigacion
        fields = [
            'nombre', 'codigo', 'descripcion', 'fecha_creacion', 
            'programa_academico', 'director', 'lineas_investigacion', 'is_active'
        ]
