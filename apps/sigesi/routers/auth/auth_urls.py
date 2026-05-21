from django.urls import path
from apps.sigesi.views.auth.login_view import LoginView, RefreshTokenView, LogoutView
from apps.sigesi.views.auth.select_role_view import SelectRoleView
from apps.sigesi.views.auth.recuperacion_view import RecuperacionView, SetPasswordView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('select-role/', SelectRoleView.as_view(), name='select_role'),
    path('refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('recuperacion/', RecuperacionView.as_view(), name='recuperacion'),
    path('recuperacion/set-password/', SetPasswordView.as_view(), name='set_password'),
]
