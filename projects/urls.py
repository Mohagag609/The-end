from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('create/', views.create_project, name='create'),
    path('<int:project_id>/', views.project_detail, name='detail'),
    path('<int:project_id>/stages/', views.stages_list, name='stages'),
    path('<int:project_id>/stages/create/', views.create_stage, name='create_stage'),
    path('<int:project_id>/stages/<int:stage_id>/', views.stage_detail, name='stage_detail'),
    path('<int:project_id>/warehouses/', views.warehouses_list, name='warehouses'),
    path('<int:project_id>/warehouses/create/', views.create_warehouse, name='create_warehouse'),
]