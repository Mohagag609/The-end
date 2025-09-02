from django.urls import path
from . import views

app_name = 'settlements'

urlpatterns = [
    path('<int:project_id>/', views.settlements_list, name='list'),
    path('<int:project_id>/create/', views.create_settlement, name='create'),
    path('<int:project_id>/batch/<int:batch_id>/', views.settlement_detail, name='detail'),
]