from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # قائمة الأصناف
    path('items/', views.items_list, name='items'),
    path('items/add/', views.add_item, name='add_item'),
    path('items/<int:item_id>/', views.item_detail, name='item_detail'),
    
    # حركات المخزون
    path('movements/', views.stock_movements, name='movements'),
    path('issue/', views.issue_stock, name='issue'),
    path('receive/', views.receive_stock, name='receive'),
    
    # المخازن
    path('warehouses/', views.warehouses_list, name='warehouses'),
    path('warehouse/<int:warehouse_id>/', views.warehouse_detail, name='warehouse_detail'),
]