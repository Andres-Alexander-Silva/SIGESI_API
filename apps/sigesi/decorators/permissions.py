from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.sigesi.models import User, GrupoInvestigacion, Actividad

class SemilleroRolePermission(BasePermission):
    """
    Control de acceso a nivel de vista y objeto para Semilleros.
    - Administrador: Acceso total.
    - Director de Grupo: Gestiona los semilleros que pertenecen a su grupo de investigación. 
                         Solo puede crear semilleros asociados a su propio grupo.
    - Director de Semillero: Gestiona solo su propio semillero (Update). No puede crear ni eliminar.
    - Estudiante / Líder Estudiantil: Acceso exclusivo de lectura.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        user = request.user
        
        # Administrador tiene acceso total
        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True
            
        # Estudiantes y líderes estudiantiles solo lectura
        if user.tiene_alguno_de([User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL]):
            return request.method in SAFE_METHODS
            
        # Director de semillero no puede crear ni eliminar
        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            if request.method in ['POST', 'DELETE']:
                return False
            return True
            
        # Director de grupo
        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            if request.method == 'POST':
                grupo_id = request.data.get('grupo_investigacion')
                if grupo_id:
                    return GrupoInvestigacion.objects.filter(id=grupo_id, director=user).exists()
                return False # Si no envía grupo, se le deniega (el serializer también lo pediría)
            return True
            
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Administrador tiene acceso total
        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True
            
        # Solo lectura para estudiantes
        if user.tiene_alguno_de([User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL]):
            return request.method in SAFE_METHODS
            
        # Director de semillero: solo puede ver/editar su propio semillero
        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            if request.method == 'DELETE':
                return False
            return obj.director == user
            
        # Director de grupo: solo puede gestionar semilleros de su grupo
        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return obj.grupo_investigacion.director == user
            
        return False


class ProyectoRolePermission(BasePermission):
    """
    Control de acceso a nivel de vista y objeto para Proyectos.
    - Administrador: Acceso total.
    - Director de Grupo / Director de Semillero: Acceso total a los proyectos asociados a su grupo/semillero.
    - Estudiante / Líder Estudiantil: Solo pueden crear en estado 'idea'. Pueden consultar y editar si están vinculados, pero no pueden cambiar de estado ni de líder libremente.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        user = request.user
        
        # Administrador tiene acceso total
        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True
            
        # Para GET, todos pueden consultar la lista (la vista filtrará el queryset)
        if request.method in SAFE_METHODS:
            return True
            
        # Creación
        if request.method == 'POST':
            return True
            
        # Edición y Eliminación: permitidas a nivel general, se controlará por objeto
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            return True
            
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Administrador tiene acceso total
        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True
            
        # Lectura
        if request.method in SAFE_METHODS:
            # Pueden ver el proyecto si están en el semillero, grupo o son parte del proyecto.
            # Asumiremos que pueden ver cualquier proyecto, o bien limitarlo. Dejaremos que puedan ver (True) para simplificar la lectura, la vista lista filtrará si es necesario.
            return True
            
        # Directores pueden gestionar proyectos de su semillero/grupo
        if user.tiene_alguno_de([User.RolChoices.DIRECTOR_SEMILLERO, User.RolChoices.DIRECTOR_GRUPO]):
            # Verificar si el proyecto pertenece a un semillero/grupo del director
            if obj.semilleros.filter(director=user).exists():
                return True
            if obj.semilleros.filter(grupo_investigacion__director=user).exists():
                return True
            if obj.director == user:
                return True
            return False
            
        # Estudiantes/Líderes solo pueden editar si son el líder o están vinculados
        if user.tiene_alguno_de([User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL]):
            if request.method == 'DELETE':
                return False  # No pueden eliminar
                
            # Solo el líder puede editar el proyecto, o estudiantes vinculados (decidiremos que solo el líder)
            if obj.lider == user:
                # La restricción de cambiar estado se manejará en el serializer o vista (change_state)
                return True
            return False
            
        return False


class InscripcionRolePermission(BasePermission):
    """
    Control de acceso para inscripciones de semillero (MatriculaSemillero).
    - Administrador: Acceso total (CRUD completo).
    - Estudiante: Puede crear (auto-inscripción), listar las suyas y retirarse (DELETE).
    - Director de Semillero: Puede listar miembros de su semillero e inscribir estudiantes.
    - Director de Grupo: Solo lectura de todas las inscripciones.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user

        # Administrador tiene acceso total
        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        # Estudiante: GET, POST, DELETE permitidos (restricción a nivel de objeto)
        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            if request.method in ('GET', 'HEAD', 'OPTIONS', 'POST', 'DELETE'):
                return True
            return False

        # Director de Semillero: GET y POST
        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            if request.method in SAFE_METHODS or request.method == 'POST':
                return True
            return False

        # Director de Grupo: solo lectura
        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return request.method in SAFE_METHODS

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Administrador tiene acceso total
        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        # Director de Grupo: puede ver cualquier inscripción
        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return request.method in SAFE_METHODS

        # Director de Semillero: puede ver inscripciones de su semillero
        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            if request.method in SAFE_METHODS:
                return obj.semillero.director == user
            return False

        # Estudiante: solo puede ver/eliminar sus propias inscripciones
        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            if obj.estudiante != user:
                return False
            if request.method in SAFE_METHODS:
                return True
            if request.method == 'DELETE':
                return obj.estado == 'activa'
            return False

        return False


class ActividadRolePermission(BasePermission):
    """
    Control de acceso a nivel de vista y objeto para Actividades.
    - Estudiante: Solo lectura.
    - Administrador, Director (Grupo/Semillero), Líder Estudiantil: Acceso total (CRUD completo).
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user

        # Administrador, Líder Estudiantil, Directores: Acceso total
        if user.tiene_alguno_de([
            User.RolChoices.ADMINISTRADOR,
            User.RolChoices.LIDER_ESTUDIANTIL,
            User.RolChoices.DIRECTOR_SEMILLERO,
            User.RolChoices.DIRECTOR_GRUPO
        ]):
            return True

        # Estudiante: Solo lectura
        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return request.method in SAFE_METHODS

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Administrador tiene acceso total
        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        # Estudiante: Solo lectura
        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return request.method in SAFE_METHODS

        # Líder Estudiantil: Acceso si es el líder del proyecto de la actividad
        if user.tiene_rol(User.RolChoices.LIDER_ESTUDIANTIL):
            if obj.proyecto.lider == user:
                return True
            return request.method in SAFE_METHODS

        # Director de Semillero: Acceso si es director del proyecto o del semillero del proyecto
        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            if obj.proyecto.director == user or obj.proyecto.semilleros.filter(director=user).exists():
                return True
            return request.method in SAFE_METHODS

        # Director de Grupo: Acceso si es director del grupo asociado a los semilleros del proyecto
        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            if obj.proyecto.semilleros.filter(grupo_investigacion__director=user).exists():
                return True
            return request.method in SAFE_METHODS

        return False


class ProduccionAcademicaRolePermission(BasePermission):
    """
    Producción Académica:
    - Administrador: CRUD total.
    - Director/Líder del proyecto vinculado: CRUD sobre las producciones de ese proyecto.
    - Cualquier otro usuario autenticado: solo lectura.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        if request.method in SAFE_METHODS:
            return True

        # POST y métodos a nivel detalle se filtran después:
        # - POST: se valida en la vista (create override) contra validated_data['proyecto'].
        # - PATCH/PUT/DELETE: se filtran en has_object_permission contra obj.proyecto.
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        if request.method in SAFE_METHODS:
            return True

        proyecto = obj.proyecto
        if proyecto and (proyecto.director_id == user.id or proyecto.lider_id == user.id):
            return True

        return False


class AdminOrReadOnlyPermission(BasePermission):
    """
    Acceso de solo lectura para cualquier usuario autenticado.
    Operaciones de escritura (POST, PUT, PATCH, DELETE) reservadas al Administrador.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return request.user.tiene_rol(User.RolChoices.ADMINISTRADOR)


class CronogramaProyectoRolePermission(BasePermission):
    """
    Control de acceso a nivel de vista y objeto para Cronogramas de Proyecto.
    - Estudiante: Solo lectura.
    - Administrador, Director (Grupo/Semillero), Líder Estudiantil: Acceso total (CRUD).
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user

        if user.tiene_alguno_de([
            User.RolChoices.ADMINISTRADOR,
            User.RolChoices.LIDER_ESTUDIANTIL,
            User.RolChoices.DIRECTOR_SEMILLERO,
            User.RolChoices.DIRECTOR_GRUPO
        ]):
            return True

        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return request.method in SAFE_METHODS

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        if user.tiene_rol(User.RolChoices.ESTUDIANTE):
            return request.method in SAFE_METHODS

        if user.tiene_rol(User.RolChoices.LIDER_ESTUDIANTIL):
            if obj.proyecto.lider == user:
                return True
            return request.method in SAFE_METHODS

        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            if obj.proyecto.director == user or obj.proyecto.semilleros.filter(director=user).exists():
                return True
            return request.method in SAFE_METHODS

        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            if obj.proyecto.semilleros.filter(grupo_investigacion__director=user).exists():
                return True
            return request.method in SAFE_METHODS

        return False


class EvidenciaRolePermission(BasePermission):
    """
    Control de acceso a nivel de vista y objeto para Evidencias.
    - El usuario asignado (responsable de la actividad) puede realizar CRUD completo.
    - Administrador puede ver todas las evidencias (solo lectura).
    - Director de Grupo puede ver todas las evidencias de los semilleros en su grupo.
    - Director de Semillero y Líder Estudiantil pueden ver todas las evidencias de su semillero.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user

        # Todos los autenticados pueden intentar hacer GET (el queryset o has_object_permission filtrará)
        if request.method in SAFE_METHODS:
            return True

        # Para crear (POST), verificamos que el usuario sea el responsable de la actividad
        if request.method == 'POST':
            actividad_id = request.data.get('actividad')
            if actividad_id:
                return Actividad.objects.filter(id=actividad_id, responsable=user).exists()
            return False

        # Para PUT, PATCH, DELETE se permitirá a nivel de vista, pero se denegará a nivel de objeto 
        # si no es el responsable.
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        # El usuario asignado a la actividad tiene permisos completos (CRUD)
        if obj.actividad.responsable == user:
            return True

        # Para los demás, solo se permite lectura (SAFE_METHODS)
        if request.method not in SAFE_METHODS:
            return False

        # Administrador puede leer todas las evidencias
        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        # Director de Grupo puede leer las evidencias de semilleros de su grupo
        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return obj.actividad.proyecto.semilleros.filter(grupo_investigacion__director=user).exists()

        # Director de Semillero y Líder Estudiantil pueden leer evidencias de su semillero
        if user.tiene_alguno_de([User.RolChoices.DIRECTOR_SEMILLERO, User.RolChoices.LIDER_ESTUDIANTIL]):
            return obj.actividad.proyecto.semilleros.filter(director=user).exists() or \
                   obj.actividad.proyecto.semilleros.filter(lider_estudiantil=user).exists()

        return False
