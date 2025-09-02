from django.urls import path
from . import views

app_name = 'settlements'

urlpatterns = [
    path('', views.settlements_list, name='list'),
    path('create/', views.create_settlement, name='create'),
    path('<int:batch_id>/', views.settlement_detail, name='detail'),
]