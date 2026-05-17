from rest_framework import serializers
from apps.sigesi.models import Proyecto, Semillero, User

class UserSimpleSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'nombre_completo', 'roles']

    def get_nombre_completo(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class ReporteAcademicoProyectoSerializer(serializers.ModelSerializer):
    director = UserSimpleSerializer(read_only=True)
    lider = UserSimpleSerializer(read_only=True)
    total_actividades = serializers.IntegerField(read_only=True, default=0)
    actividades_completadas = serializers.IntegerField(read_only=True, default=0)
    avance_global = serializers.FloatField(read_only=True, default=0.0)
    cantidad_producciones = serializers.IntegerField(read_only=True, default=0)
    estudiantes_activos_count = serializers.IntegerField(read_only=True, default=0)
    
    class Meta:
        model = Proyecto
        fields = [
            'id', 'titulo', 'codigo', 'estado', 'fecha_inicio', 'fecha_cierre',
            'director', 'lider', 'total_actividades', 'actividades_completadas',
            'avance_global', 'cantidad_producciones', 'estudiantes_activos_count'
        ]


class ReporteGlobalSemilleroSerializer(serializers.ModelSerializer):
    director = UserSimpleSerializer(read_only=True)
    total_proyectos = serializers.IntegerField(read_only=True, default=0)
    proyectos_activos = serializers.IntegerField(read_only=True, default=0)
    total_matriculas = serializers.IntegerField(read_only=True, default=0)
    total_producciones = serializers.IntegerField(read_only=True, default=0)
    
    class Meta:
        model = Semillero
        fields = [
            'id', 'nombre', 'codigo', 'fecha_creacion', 'director',
            'total_proyectos', 'proyectos_activos', 'total_matriculas', 'total_producciones'
        ]
