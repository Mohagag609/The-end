from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('<int:project_id>/', views.expenses_list, name='list'),
    path('<int:project_id>/create/', views.create_expense, name='create'),
    path('<int:project_id>/quick/', views.quick_expense, name='quick'),
]