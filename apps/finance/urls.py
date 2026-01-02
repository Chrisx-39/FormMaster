from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # Invoices
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/create/', views.InvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<int:pk>/pdf/', views.generate_invoice_pdf, name='invoice_pdf'),

    # Payments
    path('payments/create/', views.PaymentCreateView.as_view(), name='payment_create'),

    # Revenue dashboard
    path('revenue-dashboard/', views.revenue_dashboard, name='revenue_dashboard'),
]
