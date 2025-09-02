from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('project/<int:project_id>/', views.project_dashboard, name='project_dashboard'),
    path('project/<int:project_id>/kpis/', views.kpis, name='kpis'),
]