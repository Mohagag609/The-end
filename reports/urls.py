from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('<int:project_id>/', views.reports_index, name='index'),
    path('<int:project_id>/partners/', views.partners_report, name='partners'),
    path('<int:project_id>/suppliers/', views.suppliers_report, name='suppliers'),
    path('<int:project_id>/iron/', views.iron_report, name='iron'),
    path('<int:project_id>/export/', views.export_csv, name='export'),
]