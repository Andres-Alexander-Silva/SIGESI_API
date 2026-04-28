from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.sigesi.models import User, GrupoInvestigacion

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
