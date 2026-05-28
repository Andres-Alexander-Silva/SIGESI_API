from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.sigesi.models import User, GrupoInvestigacion, Actividad


def active_role(request):
    """Rol activo embebido en el access token, o ``None``.

    Lee el claim ``role`` del token validado (``request.auth``). Útil para que
    las vistas / filtros de queryset razonen sobre el rol *seleccionado* en lugar
    del conjunto completo de roles del usuario.
    """
    token = getattr(request, 'auth', None)
    return token.get('role') if token is not None else None


class UserManagementPermission(BasePermission):
    """Permisos del endpoint /users/.

    - Lectura (GET/HEAD/OPTIONS): cualquier usuario autenticado.
    - Escritura (POST/PUT/PATCH/DELETE): solo el administrador.

    La actualización del correo personal propio se expone como acción aparte con
    su propio permiso (IsAuthenticated), por lo que no pasa por esta clase.
    """
    message = 'Solo el administrador puede gestionar usuarios.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.tiene_rol(User.RolChoices.ADMINISTRADOR)


class HasRolePermission(BasePermission):
    """Exige un rol activo válido en el access token.

    - Rechaza el Identity JWT (``token_use == 'identity'``) y los tokens sin ``role``.
    - Defensa en profundidad: el rol del token debe seguir asignado en la BD.
    - Si la vista declara ``required_roles`` (lista de códigos), el rol activo
      debe pertenecer a esa lista; si no la declara, basta con tener un rol válido.

    Uso por vista::

        class MiViewSet(viewsets.ModelViewSet):
            permission_classes = [HasRolePermission]
            required_roles = ['administrador', 'director_grupo']
    """
    message = 'Su rol activo no tiene acceso a este recurso.'

    def has_permission(self, request, view):
        token = getattr(request, 'auth', None)
        if token is None or token.get('token_use') == 'identity':
            return False

        role = token.get('role')
        user = getattr(request, 'user', None)
        if not role or user is None or role not in getattr(user, 'roles', []):
            return False

        required = getattr(view, 'required_roles', None)
        if required:
            return role in required
        return True

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


class ExportarReportesPermission(BasePermission):
    """Solo Admin, Director de Grupo y Director de Semillero pueden exportar reportes."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.tiene_alguno_de([
            User.RolChoices.ADMINISTRADOR,
            User.RolChoices.DIRECTOR_GRUPO,
            User.RolChoices.DIRECTOR_SEMILLERO,
        ])


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


class PlanAccionRolePermission(BasePermission):
    """
    Control de acceso a nivel de vista y objeto para Planes de Acción.
    - Administrador: Acceso total.
    - Director de Grupo: Acceso total a los planes de los semilleros de su grupo.
    - Director de Semillero: Acceso total a los planes de su propio semillero.
    - Estudiante / Líder Estudiantil: Solo lectura.

    La aprobación (acción ``aprobar``) está restringida a Administrador y
    Director de Grupo; ese chequeo adicional vive en la vista.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user

        if user.tiene_alguno_de([
            User.RolChoices.ADMINISTRADOR,
            User.RolChoices.DIRECTOR_GRUPO,
            User.RolChoices.DIRECTOR_SEMILLERO,
        ]):
            return True

        # Estudiante / Líder Estudiantil: solo lectura.
        return request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return obj.semillero.grupo_investigacion.director == user

        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return obj.semillero.director == user

        # Resto de roles: solo lectura.
        return request.method in SAFE_METHODS


class CronogramaRolePermission(BasePermission):
    """
    Control de acceso a nivel de vista y objeto para Cronogramas.
    - Administrador: Acceso total.
    - Director de Grupo: Acceso total a los cronogramas de los semilleros de su grupo.
    - Director de Semillero: Acceso total a los cronogramas de su propio semillero.
    - Estudiante / Líder Estudiantil: Solo lectura.

    El semillero se resuelve a través de ``cronograma.plan_accion.semillero``.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user

        if user.tiene_alguno_de([
            User.RolChoices.ADMINISTRADOR,
            User.RolChoices.DIRECTOR_GRUPO,
            User.RolChoices.DIRECTOR_SEMILLERO,
        ]):
            return True

        # Estudiante / Líder Estudiantil: solo lectura.
        return request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        user = request.user
        semillero = obj.plan_accion.semillero

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return semillero.grupo_investigacion.director == user

        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return semillero.director == user

        # Resto de roles: solo lectura.
        return request.method in SAFE_METHODS


class ActividadCronogramaRolePermission(BasePermission):
    """
    Control de acceso para Actividades de Cronograma.
    Misma política que :class:`CronogramaRolePermission`; el semillero se
    resuelve a través de ``actividad.cronograma.plan_accion.semillero``.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user

        if user.tiene_alguno_de([
            User.RolChoices.ADMINISTRADOR,
            User.RolChoices.DIRECTOR_GRUPO,
            User.RolChoices.DIRECTOR_SEMILLERO,
        ]):
            return True

        return request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        user = request.user
        semillero = obj.cronograma.plan_accion.semillero

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return semillero.grupo_investigacion.director == user

        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return semillero.director == user

        return request.method in SAFE_METHODS


class PlanEstrategicoRolePermission(BasePermission):
    """
    Control de acceso a nivel de vista y objeto para Planes Estratégicos.
    - Administrador: Acceso total.
    - Director de Grupo: Acceso total a los planes de los semilleros de su grupo.
    - Director de Semillero: Acceso total a los planes de su propio semillero.
    - Estudiante / Líder Estudiantil: Solo lectura.

    Nota: el cambio del campo ``estado`` está restringido adicionalmente a
    Administrador y Director de Grupo; ese chequeo vive en el ``validate()`` del
    serializador, ya que el Director de Semillero conserva acceso total al resto
    de campos.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user

        if user.tiene_alguno_de([
            User.RolChoices.ADMINISTRADOR,
            User.RolChoices.DIRECTOR_GRUPO,
            User.RolChoices.DIRECTOR_SEMILLERO,
        ]):
            return True

        # Estudiante / Líder Estudiantil: solo lectura.
        return request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        if user.tiene_rol(User.RolChoices.DIRECTOR_GRUPO):
            return obj.semillero.grupo_investigacion.director == user

        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return obj.semillero.director == user

        # Resto de roles: solo lectura.
        return request.method in SAFE_METHODS


class CompetenciaInvestigativaRolePermission(BasePermission):
    """
    Control de acceso a nivel de vista y objeto para Competencias Investigativas.
    - Administrador: CRUD completo.
    - Director de Grupo: solo lectura de las competencias de los semilleros de su grupo.
    - Director de Semillero: lectura y actualización de las de su propio semillero
      (no puede crear ni eliminar).
    - Líder Estudiantil / Estudiante: solo lectura de las de su semillero.

    El alcance por filas (qué competencias ve cada rol) lo aplica adicionalmente
    el ``get_queryset`` de la vista.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        # Director de Semillero: lectura y actualización (sin crear ni eliminar).
        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return request.method in SAFE_METHODS or request.method in ('PUT', 'PATCH')

        # Director de Grupo / Líder Estudiantil / Estudiante: solo lectura.
        if user.tiene_alguno_de([
            User.RolChoices.DIRECTOR_GRUPO,
            User.RolChoices.LIDER_ESTUDIANTIL,
            User.RolChoices.ESTUDIANTE,
        ]):
            return request.method in SAFE_METHODS

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        # Director de Semillero: solo su propio semillero, lectura o actualización.
        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return obj.semillero.director == user and (
                request.method in SAFE_METHODS or request.method in ('PUT', 'PATCH')
            )

        # Resto de roles: solo lectura (el alcance por filas lo aplica get_queryset).
        return request.method in SAFE_METHODS


class PerfilInvestigativoRolePermission(BasePermission):
    """
    Control de acceso a nivel de vista y objeto para Perfiles Investigativos.
    - Administrador: CRUD completo.
    - Director de Grupo: solo lectura de los perfiles de estudiantes matriculados
      en semilleros de su grupo.
    - Director de Semillero: solo lectura de los perfiles de estudiantes
      matriculados en su semillero.
    - Estudiante: solo lectura de su propio perfil.
    - Líder Estudiantil: solo lectura de su propio perfil.

    El alcance por filas (qué perfil ve cada rol) lo aplica adicionalmente el
    ``get_queryset`` de la vista.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        # Director de Grupo / Director de Semillero / Estudiante / Líder
        # Estudiantil: solo lectura.
        if user.tiene_alguno_de([
            User.RolChoices.DIRECTOR_GRUPO,
            User.RolChoices.DIRECTOR_SEMILLERO,
            User.RolChoices.ESTUDIANTE,
            User.RolChoices.LIDER_ESTUDIANTIL,
        ]):
            return request.method in SAFE_METHODS

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        # Resto de roles habilitados: solo lectura (el alcance por filas lo
        # aplica get_queryset).
        if user.tiene_alguno_de([
            User.RolChoices.DIRECTOR_GRUPO,
            User.RolChoices.DIRECTOR_SEMILLERO,
            User.RolChoices.ESTUDIANTE,
            User.RolChoices.LIDER_ESTUDIANTIL,
        ]):
            return request.method in SAFE_METHODS

        return False


class EvaluacionRolePermission(BasePermission):
    """
    Control de acceso a nivel de vista y objeto para Evaluaciones de competencias.
    - Administrador: CRUD completo.
    - Director de Semillero: CRUD completo sobre las evaluaciones de su propio
      semillero (resuelto vía ``evaluacion.competencia.semillero``).
    - Director de Grupo / Líder Estudiantil / Estudiante: solo lectura.

    El alcance por filas (qué evaluaciones ve cada rol) lo aplica adicionalmente
    el ``get_queryset`` de la vista. Esta clase NO gobierna la acción
    ``calificar``: esa usa :class:`EvaluacionCalificarPermission` mediante el
    ``get_permissions`` de la vista.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user

        if user.tiene_alguno_de([
            User.RolChoices.ADMINISTRADOR,
            User.RolChoices.DIRECTOR_SEMILLERO,
        ]):
            return True

        # Director de Grupo / Líder Estudiantil / Estudiante: solo lectura.
        if user.tiene_alguno_de([
            User.RolChoices.DIRECTOR_GRUPO,
            User.RolChoices.LIDER_ESTUDIANTIL,
            User.RolChoices.ESTUDIANTE,
        ]):
            return request.method in SAFE_METHODS

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.tiene_rol(User.RolChoices.ADMINISTRADOR):
            return True

        # Director de Semillero: CRUD completo sobre su propio semillero.
        if user.tiene_rol(User.RolChoices.DIRECTOR_SEMILLERO):
            return obj.competencia.semillero.director == user

        # Resto de roles: solo lectura (el alcance por filas lo aplica get_queryset).
        return request.method in SAFE_METHODS


class EvaluacionCalificarPermission(BasePermission):
    """
    Permiso de la acción ``calificar`` de una Evaluación.
    Solo el evaluador asignado a la evaluación puede fijar el puntaje, las
    observaciones y el nivel alcanzado. Para una autoevaluación el evaluador es
    el propio estudiante; para una heteroevaluación es el usuario indicado al
    crear la evaluación.
    """
    message = 'Solo el evaluador asignado puede calificar esta evaluación.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return obj.evaluador_id == request.user.id
