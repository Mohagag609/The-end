from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_index, name='index'),
    path('partners/', views.partners_report, name='partners'),
    path('stages/', views.stages_report, name='stages'),
    path('suppliers/', views.suppliers_report, name='suppliers'),
    path('iron/', views.iron_report, name='iron'),
    path('export/<str:report_type>/', views.export_csv, name='export_csv'),
]