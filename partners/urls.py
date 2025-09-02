from django.urls import path
from . import views

app_name = 'partners'

urlpatterns = [
    # قائمة الشركاء
    path('', views.partners_list, name='list'),
    path('add/', views.add_partner, name='add'),
    path('<int:partner_id>/', views.partner_detail, name='detail'),
    
    # المحافظ
    path('wallets/', views.wallets_summary, name='wallets'),
    path('wallet/<int:partner_id>/', views.wallet_detail, name='wallet_detail'),
    
    # السندات
    path('voucher/receipt/', views.create_receipt, name='create_receipt'),
    path('voucher/payment/', views.create_payment, name='create_payment'),
    path('vouchers/', views.vouchers_list, name='vouchers'),
]