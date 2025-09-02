from django.urls import path
from . import views

app_name = 'allocations'

urlpatterns = [
    path('<int:project_id>/stage/<int:stage_id>/', views.allocate_delta, name='allocate'),
    path('<int:project_id>/history/', views.allocations_history, name='history'),
]