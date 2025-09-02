from django.contrib import admin
from .models import Project, Stage, Warehouse

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'status', 'currency', 'created_at']
    list_filter = ['status', 'currency']
    search_fields = ['code', 'name']
    date_hierarchy = 'created_at'

@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'budget', 'status', 'created_at']
    list_filter = ['status', 'project']
    search_fields = ['name', 'project__name']
    date_hierarchy = 'created_at'

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'location', 'is_active']
    list_filter = ['is_active', 'project']
    search_fields = ['name', 'location', 'project__name']