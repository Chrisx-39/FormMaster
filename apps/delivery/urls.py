from django.urls import path
from . import views

app_name = 'delivery'

urlpatterns = [
    # Transport Requests
    path('transport/', views.TransportRequestListView.as_view(), name='transport_list'),
    path('transport/create/', views.TransportRequestCreateView.as_view(), name='transport_create'),
    path('transport/<int:pk>/', views.TransportRequestDetailView.as_view(), name='transport_detail'),
    path('transport/<int:pk>/approve/', views.TransportRequestApproveView.as_view(), name='transport_approve'),
    path('transport/<int:pk>/update/', views.TransportRequestUpdateView.as_view(), name='transport_update'),
    path('transport/<int:pk>/cancel/', views.TransportRequestCancelView.as_view(), name='transport_cancel'),
    
    # Deliveries
    path('deliveries/', views.DeliveryListView.as_view(), name='delivery_list'),
    path('deliveries/create/', views.DeliveryCreateView.as_view(), name='delivery_create'),
    path('deliveries/<int:pk>/', views.DeliveryDetailView.as_view(), name='delivery_detail'),
    path('deliveries/<int:pk>/update/', views.DeliveryUpdateView.as_view(), name='delivery_update'),
    path('deliveries/<int:pk>/mark-delivered/', views.DeliveryMarkAsDeliveredView.as_view(), name='delivery_mark_delivered'),
    
    # Delivery Notes
    path('delivery-notes/<int:pk>/', views.DeliveryNoteDetailView.as_view(), name='delivery_note_detail'),
    path('delivery-notes/<int:pk>/update/', views.DeliveryNoteUpdateView.as_view(), name='delivery_note_update'),
    path('delivery-notes/<int:pk>/update-items/', views.DeliveryNoteItemsUpdateView.as_view(), name='delivery_note_items_update'),
    path('delivery-notes/<int:pk>/sign/<str:role>/', views.sign_delivery_note, name='delivery_note_sign'),
    path('delivery-notes/<int:pk>/pdf/', views.generate_delivery_note_pdf, name='delivery_note_pdf'),
    
    # Goods Received Vouchers
    path('grv/', views.GoodsReceivedVoucherListView.as_view(), name='grv_list'),
    path('grv/create/', views.GoodsReceivedVoucherCreateView.as_view(), name='grv_create'),
    path('grv/<int:pk>/', views.GoodsReceivedVoucherDetailView.as_view(), name='grv_detail'),
    path('grv/<int:pk>/update/', views.GoodsReceivedVoucherUpdateView.as_view(), name='grv_update'),
    path('grv/<int:pk>/pdf/', views.generate_grv_pdf, name='grv_pdf'),
    
    # AJAX endpoints
    path('ajax/get-order-details/<int:order_id>/', views.get_order_details, name='get_order_details'),
    path('ajax/get-delivery-note-items/<int:delivery_id>/', views.get_delivery_note_items, name='get_delivery_note_items'),
]