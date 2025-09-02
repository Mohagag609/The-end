from django.urls import path
from . import views

app_name = 'partners'

urlpatterns = [
    path('<int:project_id>/', views.partners_list, name='list'),
    path('<int:project_id>/add/', views.add_partner, name='add'),
    path('<int:project_id>/voucher/receipt/', views.create_receipt, name='create_receipt'),
    path('<int:project_id>/voucher/payment/', views.create_payment, name='create_payment'),
    path('<int:project_id>/wallets/', views.wallets_summary, name='wallets'),
    path('<int:project_id>/statement/', views.partners_statement, name='statement'),
]