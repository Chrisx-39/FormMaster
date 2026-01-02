from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Dashboard
    path('', views.inventory_dashboard, name='dashboard'),
    
   
    
    # Materials
    path('materials/', views.material_list, name='material_list'),
    path('materials/create/', views.material_create, name='material_create'),
    path('materials/<int:pk>/', views.material_detail, name='material_detail'),
    path('materials/<int:pk>/edit/', views.material_update, name='material_edit'),
    path('materials/<int:pk>/delete/', views.material_delete, name='material_delete'),
    path('materials/<int:pk>/inspect/', views.material_inspect, name='material_inspect'),
    path('materials/<int:pk>/adjust-stock/', views.material_adjust_stock, name='material_adjust_stock'),
    
  
    # API/JSON endpoints
    path('api/check-availability/', views.check_availability, name='check_availability'),
    path('export/', views.export_inventory, name='export_inventory'),
]