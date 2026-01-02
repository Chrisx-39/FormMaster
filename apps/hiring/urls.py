from django.urls import path
from . import views

app_name = 'hiring'

urlpatterns = [
    # RFQs
    path('rfqs/', views.rfq_list, name='rfq_list'),
    path('rfqs/create/', views.rfq_create, name='rfq_create'),
    path('rfqs/<int:pk>/', views.rfq_detail, name='rfq_detail'),
    path('rfqs/<int:pk>/convert/', views.rfq_convert_to_quotation, name='rfq_convert_to_quotation'),
    path('rfqs/<int:pk>/edit/', views.rfq_update, name='rfq_edit'),
    path('rfqs/<int:pk>/delete/', views.rfq_delete, name='rfq_delete'),
    
    # Quotations
    path('quotations/', views.quotation_list, name='quotation_list'),
    path('quotations/create/', views.quotation_create, name='quotation_create'),
    path('quotations/<int:pk>/', views.quotation_detail, name='quotation_detail'),
    path('quotations/<int:pk>/approve/', views.quotation_approve, name='quotation_approve'),
    path('quotations/<int:pk>/send/', views.quotation_send_to_client, name='quotation_send'),
    path('quotations/<int:pk>/accept/', views.quotation_accept, name='quotation_accept'),
    path('quotations/<int:pk>/edit/', views.quotation_update, name='quotation_edit'),
    path('quotations/<int:pk>/delete/', views.quotation_delete, name='quotation_delete'),
    path('quotations/<int:quotation_pk>/create-order/', views.create_order_from_quotation, name='create_order_from_quotation'),
    
    # Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/create/', views.order_create, name='order_create'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/edit/', views.order_update, name='order_edit'),
    path('orders/<int:pk>/update-status/<str:status>/', views.order_update_status, name='order_update_status'),
    path('orders/<int:order_pk>/create-lease/', views.create_lease_agreement, name='create_lease_agreement'),
    
    # Lease Agreements
    path('leases/', views.lease_list, name='lease_list'),
    path('leases/<int:pk>/', views.lease_detail, name='lease_detail'),
    path('leases/<int:pk>/sign-client/', views.lease_sign_client, name='lease_sign_client'),
    path('leases/<int:pk>/sign-fsm/', views.lease_sign_fsm, name='lease_sign_fsm'),
    path('leases/<int:pk>/download/', views.lease_download, name='lease_download'),
    
    # AJAX endpoints
    path('ajax/get-material-rate/<int:material_id>/', views.get_material_rate, name='get_material_rate'),
    path('ajax/check-inventory-availability/', views.check_inventory_availability, name='check_inventory_availability'),
]