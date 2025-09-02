from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('<int:project_id>/', views.inventory_list, name='list'),
    path('<int:project_id>/items/', views.items_list, name='items'),
    path('<int:project_id>/items/add/', views.add_item, name='add_item'),
    path('<int:project_id>/item/<int:item_id>/', views.item_movements, name='item_movements'),
    path('<int:project_id>/issue/', views.issue_stock, name='issue'),
    path('<int:project_id>/receive/', views.receive_stock, name='receive'),
    path('<int:project_id>/movements/', views.stock_movements, name='movements'),
]