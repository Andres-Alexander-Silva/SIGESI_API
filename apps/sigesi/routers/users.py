from django.urls import path
from apps.sigesi.views.users import create_user

urlpatterns = [
    path('users/', create_user, name='create_user'),
]
