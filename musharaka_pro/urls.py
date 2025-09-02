"""
URL configuration for musharaka_pro project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('projects/', include('projects.urls')),
    path('partners/', include('partners.urls')),
    path('suppliers/', include('suppliers.urls')),
    path('inventory/', include('inventory.urls')),
    path('purchases/', include('purchases.urls')),
    path('expenses/', include('expenses.urls')),
    path('allocations/', include('allocations.urls')),
    path('settlements/', include('settlements.urls')),
    path('reports/', include('reports.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
