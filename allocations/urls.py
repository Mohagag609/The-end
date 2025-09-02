from django.urls import path
from . import views

app_name = 'allocations'

urlpatterns = [
    path('', views.allocations_history, name='list'),
    path('stage/<int:stage_id>/', views.allocate_delta, name='allocate'),
]