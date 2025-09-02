from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('<int:project_id>/', views.inventory_list, name='list'),
    path('<int:project_id>/items/', views.items_list, name='items'),
    path('<int:project_id>/issue/', views.issue_stock, name='issue'),
    path('<int:project_id>/movements/', views.stock_movements, name='movements'),
]