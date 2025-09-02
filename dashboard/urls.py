from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('project/<int:project_id>/', views.project_dashboard, name='project_dashboard'),
    path('kpis/', views.kpis_dashboard, name='kpis'),
]