from django.urls import path
from apps.sigesi.views.config.user_view import create_user

urlpatterns = [
    path('users/', create_user, name='create_user'),
]
