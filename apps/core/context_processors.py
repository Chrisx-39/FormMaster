from datetime import datetime, timedelta
from django.utils import timezone
from apps.hiring.models import HireOrder
from apps.inventory.models import Material
from apps.finance.models import Invoice

def user_role_processor(request):
    """Add user role information to template context"""
    context = {}
    
    if request.user.is_authenticated:
        context['user_role'] = request.user.role
        context['is_admin'] = request.user.is_admin()
        context['is_fsm'] = request.user.is_fsm()
        context['is_hce'] = request.user.is_hce()
        context['is_scaffolder'] = request.user.is_scaffolder()
        
        # Add notification counts
        if request.user.is_hce or request.user.is_admin:
            # Pending RFQs
            pending_rfqs = request.user.rfqs_received.filter(status='RECEIVED').count()
            context['pending_rfqs_count'] = pending_rfqs
            
            # Pending orders for approval
            pending_orders = HireOrder.objects.filter(
                status='ORDERED',
                created_by=request.user
            ).count()
            context['pending_orders_count'] = pending_orders
            
        if request.user.is_fsm or request.user.is_admin:
            # Quotations needing approval
            pending_quotations = HireOrder.objects.filter(
                quotation__total_amount__gte=10000,
                status='ORDERED'
            ).count()
            context['pending_quotations_count'] = pending_quotations
            
            # Transport requests pending approval
            from apps.delivery.models import TransportRequest
            pending_transport = TransportRequest.objects.filter(
                status='PENDING'
            ).count()
            context['pending_transport_count'] = pending_transport
            
        if request.user.is_scaffolder or request.user.is_admin:
            # Pending inspections
            from apps.delivery.models import Delivery
            pending_inspections = Delivery.objects.filter(
                status='SCHEDULED',
                is_safe_for_transport=False
            ).count()
            context['pending_inspections_count'] = pending_inspections
    
    return context

def system_stats_processor(request):
    """Add system statistics to template context"""
    context = {}
    
    # Active rentals count
    active_rentals = HireOrder.objects.filter(status='ACTIVE').count()
    context['active_rentals_count'] = active_rentals
    
    # Overdue rentals
    overdue_rentals = HireOrder.objects.filter(
        status='ACTIVE',
        expected_return_date__lt=timezone.now().date()
    ).count()
    context['overdue_rentals_count'] = overdue_rentals
    
    # Low stock items
    low_stock_items = Material.objects.filter(
        available_quantity__lte=models.F('minimum_stock_level')
    ).count()
    context['low_stock_items_count'] = low_stock_items
    
    # Overdue invoices
    overdue_invoices = Invoice.objects.filter(
        payment_status__in=['ISSUED', 'SENT', 'PARTIAL'],
        due_date__lt=timezone.now().date()
    ).count()
    context['overdue_invoices_count'] = overdue_invoices
    
    # Today's deliveries
    today = timezone.now().date()
    todays_deliveries = Delivery.objects.filter(
        departure_time__date=today
    ).count()
    context['todays_deliveries_count'] = todays_deliveries
    
    return context