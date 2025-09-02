from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.stages_list, name='stages'),
    path('add/', views.add_stage, name='add_stage'),
    path('<int:stage_id>/', views.stage_detail, name='stage_detail'),
    path('warehouses/', views.warehouses_list, name='warehouses'),
    path('warehouse/add/', views.add_warehouse, name='add_warehouse'),
]