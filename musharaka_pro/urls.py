from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from dashboard import views as dashboard_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # الصفحة الرئيسية
    path('', dashboard_views.home, name='home'),
    
    # صفحات المشروع
    path('project/<int:project_id>/', dashboard_views.project_dashboard, name='project_dashboard'),
    path('project/<int:project_id>/kpis/', dashboard_views.kpis, name='project_kpis'),
    path('project/<int:project_id>/partners/', include('partners.urls')),
    path('project/<int:project_id>/inventory/', include('inventory.urls')),
    path('project/<int:project_id>/purchases/', include('purchases.urls')),
    path('project/<int:project_id>/expenses/', include('expenses.urls')),
    path('project/<int:project_id>/allocations/', include('allocations.urls')),
    path('project/<int:project_id>/settlements/', include('settlements.urls')),
    path('project/<int:project_id>/reports/', include('reports.urls')),
    path('project/<int:project_id>/stages/', include('projects.urls')),
    
    # صفحات عامة (غير مرتبطة بمشروع)
    path('suppliers/', include('suppliers.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)