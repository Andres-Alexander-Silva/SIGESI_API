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
        if user.rol == User.RolChoices.ADMINISTRADOR:
            return True
            
        # Estudiantes y líderes estudiantiles solo lectura
        if user.rol in [User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL]:
            return request.method in SAFE_METHODS
            
        # Director de semillero no puede crear ni eliminar
        if user.rol == User.RolChoices.DIRECTOR_SEMILLERO:
            if request.method in ['POST', 'DELETE']:
                return False
            return True
            
        # Director de grupo
        if user.rol == User.RolChoices.DIRECTOR_GRUPO:
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
        if user.rol == User.RolChoices.ADMINISTRADOR:
            return True
            
        # Solo lectura para estudiantes
        if user.rol in [User.RolChoices.ESTUDIANTE, User.RolChoices.LIDER_ESTUDIANTIL]:
            return request.method in SAFE_METHODS
            
        # Director de semillero: solo puede ver/editar su propio semillero
        if user.rol == User.RolChoices.DIRECTOR_SEMILLERO:
            if request.method == 'DELETE':
                return False
            return obj.director == user
            
        # Director de grupo: solo puede gestionar semilleros de su grupo
        if user.rol == User.RolChoices.DIRECTOR_GRUPO:
            return obj.grupo_investigacion.director == user
            
        return False
