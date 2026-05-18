from rest_framework import serializers

from apps.sigesi.models import ProduccionAcademica, Proyecto
from apps.sigesi.utils.aval import validar_semilleros_avalados


class ProduccionAcademicaListSerializer(serializers.ModelSerializer):
    """Serializer de lectura/detalle para ProduccionAcademica."""

    proyecto_titulo = serializers.CharField(source='proyecto.titulo', read_only=True)
    semillero_nombre = serializers.CharField(source='semillero.nombre', read_only=True)
    linea_investigacion_nombre = serializers.CharField(
        source='linea_investigacion.nombre', read_only=True
    )
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    autores_nombres = serializers.SerializerMethodField()

    class Meta:
        model = ProduccionAcademica
        fields = [
            'id', 'titulo', 'tipo', 'tipo_display', 'descripcion',
            'proyecto', 'proyecto_titulo',
            'semillero', 'semillero_nombre',
            'linea_investigacion', 'linea_investigacion_nombre',
            'autores', 'autores_nombres',
            'doi', 'url_repositorio', 'revista_evento', 'fecha_publicacion',
            'estado', 'estado_display',
            'archivo', 'certificado',
            'created_at', 'updated_at',
        ]

    def get_autores_nombres(self, obj):
        return [
            (autor.get_full_name() or autor.email or autor.username)
            for autor in obj.autores.all()
        ]


class ProduccionAcademicaCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para crear y actualizar ProduccionAcademica.

    Aunque el modelo permite `proyecto` nulo, este endpoint lo exige porque
    las producciones académicas se gestionan en el contexto de un proyecto.
    """

    proyecto = serializers.PrimaryKeyRelatedField(
        queryset=Proyecto.objects.all(),
        required=True,
        allow_null=False,
        error_messages={
            'required': 'El proyecto es obligatorio.',
            'null': 'El proyecto no puede ser nulo.',
            'does_not_exist': 'El proyecto seleccionado no existe.',
        },
    )

    class Meta:
        model = ProduccionAcademica
        fields = [
            'titulo', 'tipo', 'descripcion',
            'proyecto', 'semillero', 'linea_investigacion',
            'autores',
            'doi', 'url_repositorio', 'revista_evento', 'fecha_publicacion',
            'estado', 'archivo', 'certificado',
        ]

    def validate(self, data):
        semillero = data.get('semillero') or (
            self.instance.semillero if self.instance else None
        )
        if semillero:
            request = self.context.get('request')
            user = request.user if request else None
            validar_semilleros_avalados([semillero], user, field_name='semillero')
        return data
