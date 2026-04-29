from rest_framework import serializers
from apps.sigesi.models import LineaInvestigacion

class LineaInvestigacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaInvestigacion
        fields = ['id', 'nombre', 'descripcion', 'is_active', 'created_at', 'updated_at']

class LineaInvestigacionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaInvestigacion
        fields = ['nombre', 'descripcion', 'is_active']

class LineaInvestigacionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaInvestigacion
        fields = ['nombre', 'descripcion', 'is_active']
