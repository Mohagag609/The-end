from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.project_dashboard, name='project_dashboard'),
    path('kpis/', views.kpis, name='kpis'),
]