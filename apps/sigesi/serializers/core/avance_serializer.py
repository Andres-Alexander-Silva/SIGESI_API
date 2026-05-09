import os
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.sigesi.models import Avance, EvidenciaAvance, Proyecto

User = get_user_model()

# ---------------------------------------------------------------------------
# Tipos y tamaño máximo de archivos permitidos
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'docx'}
MAX_FILE_SIZE_MB   = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def _validate_file(archivo):
    """Valida extensión y tamaño del archivo de evidencia."""
    ext = os.path.splitext(archivo.name)[1].lstrip('.').lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise serializers.ValidationError(
            f"Tipo de archivo no permitido: '.{ext}'. "
            f"Tipos aceptados: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )
    if archivo.size > MAX_FILE_SIZE_BYTES:
        mb = archivo.size / (1024 * 1024)
        raise serializers.ValidationError(
            f"El archivo supera el tamaño máximo permitido de {MAX_FILE_SIZE_MB} MB "
            f"(tamaño actual: {mb:.2f} MB)."
        )
    return archivo


# ---------------------------------------------------------------------------
# Serializer de evidencias (lectura)
# ---------------------------------------------------------------------------

class EvidenciaAvanceListSerializer(serializers.ModelSerializer):
    """
    Serializador de solo lectura para Evidencias de Avance.
    """
    subido_por_nombre = serializers.SerializerMethodField(read_only=True)
    archivo_url       = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = EvidenciaAvance
        fields = [
            'id', 'avance', 'titulo', 'descripcion',
            'archivo', 'archivo_url',
            'subido_por', 'subido_por_nombre',
            'created_at', 'updated_at',
        ]

    def get_subido_por_nombre(self, obj):
        if obj.subido_por:
            return obj.subido_por.get_full_name() or obj.subido_por.email
        return None

    def get_archivo_url(self, obj):
        request = self.context.get('request')
        if obj.archivo and request:
            return request.build_absolute_uri(obj.archivo.url)
        return obj.archivo.url if obj.archivo else None


# ---------------------------------------------------------------------------
# Serializer de avances (lectura / listado)
# ---------------------------------------------------------------------------

class AvanceListSerializer(serializers.ModelSerializer):
    """
    Serializador para listar y consultar el detalle de un Avance.
    Incluye los campos de lectura enriquecidos y las evidencias anidadas.
    """
    proyecto_titulo     = serializers.CharField(source='proyecto.titulo', read_only=True)
    registrado_por_nombre = serializers.SerializerMethodField(read_only=True)
    evidencias          = EvidenciaAvanceListSerializer(many=True, read_only=True)

    class Meta:
        model  = Avance
        fields = [
            'id', 'proyecto', 'proyecto_titulo',
            'registrado_por', 'registrado_por_nombre',
            'descripcion', 'fecha', 'porcentaje', 'estado', 'observaciones',
            'evidencias',
            'created_at', 'updated_at',
        ]

    def get_registrado_por_nombre(self, obj):
        if obj.registrado_por:
            return obj.registrado_por.get_full_name() or obj.registrado_por.email
        return None


# ---------------------------------------------------------------------------
# Serializer para crear / actualizar avances (con evidencia opcional)
# ---------------------------------------------------------------------------

class AvanceCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializador para crear y actualizar Avances.

    Soporta carga de un archivo de evidencia de forma opcional mediante
    multipart/form-data (campo 'archivo').  El archivo se valida en cuanto
    a extensión y tamaño antes de persistir.

    Validaciones de negocio:
      - La descripción es obligatoria.
      - La fecha debe tener un formato válido (gestionado por DRF).
      - El porcentaje debe estar entre 0 y 100.
      - El usuario autenticado debe pertenecer al proyecto.
      - Si se adjunta archivo: extensión y tamaño permitidos.
    """
    # Campo opcional para recibir el archivo de evidencia en la misma petición
    archivo          = serializers.FileField(write_only=True, required=False, allow_null=True)
    titulo_evidencia = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default='',
        help_text='Título de la evidencia (opcional).'
    )
    descripcion_evidencia = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default='',
        help_text='Descripción de la evidencia (opcional).'
    )

    class Meta:
        model  = Avance
        fields = [
            'proyecto', 'descripcion', 'fecha', 'porcentaje', 'estado',
            'observaciones',
            # Campos de evidencia (write-only)
            'archivo', 'titulo_evidencia', 'descripcion_evidencia',
        ]

    # ------------------------------------------------------------------
    # Validaciones de campo
    # ------------------------------------------------------------------

    def validate_porcentaje(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "El porcentaje debe estar entre 0 y 100."
            )
        return value

    def validate_archivo(self, value):
        if value is None:
            return value
        return _validate_file(value)

    # ------------------------------------------------------------------
    # Validación de conjunto (cross-field)
    # ------------------------------------------------------------------

    def validate(self, data):
        request = self.context.get('request')
        user    = request.user if request else None
        proyecto = data.get('proyecto') or (self.instance.proyecto if self.instance else None)

        # 1. El proyecto debe existir (DRF PrimaryKeyRelatedField ya lo valida)
        # 2. El usuario debe pertenecer al proyecto
        if user and proyecto:
            is_admin    = user.tiene_rol(User.RolChoices.ADMINISTRADOR)
            is_director = user.tiene_alguno_de([
                User.RolChoices.DIRECTOR_GRUPO,
                User.RolChoices.DIRECTOR_SEMILLERO,
            ])
            is_member = (
                proyecto.director == user
                or proyecto.lider == user
                or proyecto.estudiantes.filter(pk=user.pk).exists()
                or proyecto.semilleros.filter(director=user).exists()
                or proyecto.semilleros.filter(grupo_investigacion__director=user).exists()
            )
            if not (is_admin or is_director or is_member):
                raise serializers.ValidationError(
                    {"proyecto": "No perteneces al proyecto indicado."}
                )

        # 3. Los estudiantes solo pueden crear/editar en estado 'borrador' o 'enviado'
        if user and user.tiene_rol(User.RolChoices.ESTUDIANTE):
            estado = data.get('estado', Avance.EstadoChoices.BORRADOR)
            if estado not in (Avance.EstadoChoices.BORRADOR, Avance.EstadoChoices.ENVIADO):
                raise serializers.ValidationError(
                    {"estado": "Los estudiantes solo pueden usar los estados 'borrador' o 'enviado'."}
                )

        return data

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def _handle_evidencia(self, avance, archivo, titulo, descripcion, user):
        """Crea el registro EvidenciaAvance si se recibió un archivo."""
        if archivo:
            EvidenciaAvance.objects.create(
                avance=avance,
                titulo=titulo or archivo.name,
                descripcion=descripcion or '',
                archivo=archivo,
                subido_por=user,
            )

    def create(self, validated_data):
        request    = self.context.get('request')
        user       = request.user if request else None

        archivo              = validated_data.pop('archivo', None)
        titulo_evidencia     = validated_data.pop('titulo_evidencia', '')
        descripcion_evidencia = validated_data.pop('descripcion_evidencia', '')

        # Asignar automáticamente el usuario como registrado_por
        validated_data['registrado_por'] = user

        avance = Avance.objects.create(**validated_data)
        self._handle_evidencia(avance, archivo, titulo_evidencia, descripcion_evidencia, user)
        return avance

    def update(self, instance, validated_data):
        request = self.context.get('request')
        user    = request.user if request else None

        archivo              = validated_data.pop('archivo', None)
        titulo_evidencia     = validated_data.pop('titulo_evidencia', '')
        descripcion_evidencia = validated_data.pop('descripcion_evidencia', '')

        # Los estudiantes no pueden cambiar el estado a estados de revisión/aprobación
        if user and user.tiene_rol(User.RolChoices.ESTUDIANTE):
            validated_data.pop('estado', None)
            validated_data.pop('observaciones', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        self._handle_evidencia(instance, archivo, titulo_evidencia, descripcion_evidencia, user)
        return instance
