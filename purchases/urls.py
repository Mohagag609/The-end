from django.urls import path
from . import views

app_name = 'purchases'

urlpatterns = [
    path('<int:project_id>/', views.purchases_list, name='list'),
    path('<int:project_id>/create/', views.create_purchase, name='create'),
    path('<int:project_id>/invoice/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
]