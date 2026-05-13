from django.urls import path
from apps.sigesi.views.core.dashboard_view import DashboardView

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
]
