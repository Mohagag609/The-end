from django.urls import path
from . import views

app_name = 'suppliers'

urlpatterns = [
    path('', views.suppliers_list, name='list'),
    path('create/', views.create_supplier, name='create'),
    path('<int:supplier_id>/', views.supplier_detail, name='detail'),
    path('<int:supplier_id>/statement/', views.supplier_statement, name='statement'),
    path('<int:supplier_id>/payment/', views.supplier_payment, name='payment'),
]