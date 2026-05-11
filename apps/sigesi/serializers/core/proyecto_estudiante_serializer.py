from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from django.contrib.auth import get_user_model
from apps.sigesi.models import ProyectoEstudiante, Proyecto

User = get_user_model()

class ProyectoEstudianteListSerializer(serializers.ModelSerializer):
    """
    Serializer para listar y consultar detalles de las participaciones de estudiantes en proyectos.
    """
    estudiante_nombre = serializers.SerializerMethodField(read_only=True)
    proyecto_titulo = serializers.CharField(source='proyecto.titulo', read_only=True)
    rol_en_proyecto_display = serializers.CharField(source='get_rol_en_proyecto_display', read_only=True)
    estado_participacion_display = serializers.CharField(source='get_estado_participacion_display', read_only=True)

    class Meta:
        model = ProyectoEstudiante
        fields = [
            'id', 'proyecto', 'proyecto_titulo', 'estudiante', 'estudiante_nombre',
            'rol_en_proyecto', 'rol_en_proyecto_display', 'fecha_asignacion', 
            'estado_participacion', 'estado_participacion_display', 'observaciones',
            'created_at', 'updated_at'
        ]

    def get_estudiante_nombre(self, obj):
        return obj.estudiante.get_full_name() or obj.estudiante.email


class ProyectoEstudianteCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para asignar o actualizar la participación de un estudiante en un proyecto.
    """
    class Meta:
        model = ProyectoEstudiante
        fields = [
            'proyecto', 'estudiante', 'rol_en_proyecto', 
            'estado_participacion', 'observaciones'
        ]
        validators = [
            UniqueTogetherValidator(
                queryset=ProyectoEstudiante.objects.all(),
                fields=['proyecto', 'estudiante'],
                message='Este estudiante ya está asociado a este proyecto.'
            )
        ]

    def validate(self, data):
        request = self.context.get('request')
        user = request.user if request else None

        proyecto = data.get('proyecto') or (self.instance.proyecto if self.instance else None)
        estudiante = data.get('estudiante') or (self.instance.estudiante if self.instance else None)

        if not proyecto:
            raise serializers.ValidationError({"proyecto": "El proyecto es requerido."})

        if not estudiante:
            raise serializers.ValidationError({"estudiante": "El estudiante es requerido."})

        # 1. Proyecto activo
        if not proyecto.is_active:
            raise serializers.ValidationError({"proyecto": "El proyecto no está activo."})

        # 2. Relación válida con semillero
        # Validar que el estudiante pertenezca a alguno de los semilleros del proyecto.
        # Asumiendo que el modelo Matrícula relaciona estudiantes con semilleros de forma activa.
        proyecto_semilleros = proyecto.semilleros.all()
        if proyecto_semilleros.exists():
            pertenece_semillero = estudiante.matriculas_semillero.filter(
                semillero__in=proyecto_semilleros, 
                estado='activa'  # Validar que la matrícula esté activa
            ).exists()
            
            if not pertenece_semillero:
                # Si no está en ninguna matrícula activa, podría ser el líder o director? 
                # El req dice: "Estudiantes pertenecientes al mismo semillero"
                # Pero si el rol es INVESTIGADOR o el user es un líder que se asignó, permitámoslo si es el mismo usuario.
                # Como requerimiento estricto:
                raise serializers.ValidationError({
                    "estudiante": "El estudiante no tiene una matrícula activa en los semilleros asociados al proyecto."
                })

        # Validaciones de permisos (RBAC) se hacen principalmente en la vista/permisos,
        # pero aquí podemos asegurar que si el usuario es un Estudiante, no se asigne a otros.
        # (Aunque el permiso bloquea esto, añadimos una capa extra por seguridad)
        if user and user.tiene_rol(User.RolChoices.ESTUDIANTE):
            if estudiante != user:
                raise serializers.ValidationError({"estudiante": "Un estudiante solo puede gestionar su propia participación."})

        return data
