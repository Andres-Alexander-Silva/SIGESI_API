from rest_framework import serializers
from apps.sigesi.models import Menu, Opcion, Permiso


class MenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menu
        fields = ['id', 'nombre', 'icono', 'estado']


class OpcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Opcion
        fields = ['id', 'menu', 'nombre', 'url', 'estado']


class PermisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permiso
        fields = [
            'id', 'rol', 'opcion',
            'puede_consultar', 'puede_crear',
            'puede_actualizar', 'puede_eliminar',
        ]
