from django.urls import path
from apps.sigesi.views.health import ping, health

urlpatterns = [
    path('ping/', ping, name='ping'),
    path('health/', health, name='health'),
]
