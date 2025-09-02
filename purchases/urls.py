from django.urls import path
from . import views

app_name = 'purchases'

urlpatterns = [
    path('', views.purchases_list, name='list'),
    path('create/', views.create_purchase, name='create'),
    path('invoice/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
]