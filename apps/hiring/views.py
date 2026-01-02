from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import (
    RequestForQuotation, RFQItem, Quotation, 
    QuotationItem, HireOrder, HireOrderItem, LeaseAgreement
)
from .forms import (
    RFQForm, RFQItemFormSet, QuotationForm,
    QuotationItemFormSet, HireOrderForm, HireOrderItemFormSet,
    LeaseAgreementForm
)
from apps.clients.models import Client
from apps.inventory.models import Material
from apps.finance.models import Invoice

@login_required
def rfq_list(request):
    """List all RFQs"""
    if not request.user.is_hce and not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'You do not have permission to view RFQs.')
        return redirect('dashboard')
    
    rfqs = RequestForQuotation.objects.all().order_by('-received_date')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        rfqs = rfqs.filter(status=status_filter)
    
    # Filter by client
    client_filter = request.GET.get('client', '')
    if client_filter:
        rfqs = rfqs.filter(client_id=client_filter)
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if date_from:
        rfqs = rfqs.filter(received_date__date__gte=date_from)
    if date_to:
        rfqs = rfqs.filter(received_date__date__lte=date_to)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        rfqs = rfqs.filter(
            Q(rfq_number__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(rfqs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    clients = Client.objects.filter(is_active=True)
    
    context = {
        'rfqs': page_obj,
        'status_filter': status_filter,
        'client_filter': client_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        'clients': clients,
        'status_choices': RequestForQuotation.STATUS_CHOICES,
    }
    
    return render(request, 'hiring/rfq_list.html', context)

@login_required
def rfq_create(request):
    """Create new RFQ"""
    if not request.user.is_hce and not request.user.is_admin:
        messages.error(request, 'Only HCE or Administrators can create RFQs.')
        return redirect('hiring:rfq_list')
    
    if request.method == 'POST':
        form = RFQForm(request.POST)
        formset = RFQItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            rfq = form.save(commit=False)
            rfq.received_by = request.user
            rfq.save()
            
            # Save items
            for item_form in formset:
                if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                    item = item_form.save(commit=False)
                    item.rfq = rfq
                    item.save()
            
            messages.success(request, f'RFQ {rfq.rfq_number} created successfully!')
            return redirect('hiring:rfq_detail', pk=rfq.pk)
    else:
        form = RFQForm()
        formset = RFQItemFormSet(queryset=RFQItem.objects.none())
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'Create New RFQ',
    }
    
    return render(request, 'hiring/rfq_form.html', context)

@login_required
def rfq_detail(request, pk):
    """View RFQ details"""
    if not request.user.is_hce and not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'You do not have permission to view RFQ details.')
        return redirect('hiring:rfq_list')
    
    rfq = get_object_or_404(RequestForQuotation, pk=pk)
    
    # Check if quotation already exists
    quotation_exists = Quotation.objects.filter(rfq=rfq).exists()
    
    context = {
        'rfq': rfq,
        'quotation_exists': quotation_exists,
    }
    
    return render(request, 'hiring/rfq_detail.html', context)

@login_required
def rfq_convert_to_quotation(request, pk):
    """Convert RFQ to quotation"""
    if not request.user.is_hce and not request.user.is_admin:
        messages.error(request, 'Only HCE or Administrators can create quotations.')
        return redirect('hiring:rfq_detail', pk=pk)
    
    rfq = get_object_or_404(RequestForQuotation, pk=pk)
    
    # Check if quotation already exists
    if Quotation.objects.filter(rfq=rfq).exists():
        messages.warning(request, 'A quotation already exists for this RFQ.')
        return redirect('hiring:rfq_detail', pk=rfq.pk)
    
    if request.method == 'POST':
        form = QuotationForm(request.POST)
        formset = QuotationItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            quotation = form.save(commit=False)
            quotation.rfq = rfq
            quotation.prepared_by = request.user
            quotation.hire_duration_days = rfq.hire_duration_days
            quotation.valid_until = timezone.now().date() + timedelta(days=7)
            quotation.save()
            
            # Save items
            for item_form in formset:
                if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                    item = item_form.save(commit=False)
                    item.quotation = quotation
                    item.save()
            
            # Calculate totals
            quotation.calculate_totals()
            quotation.save()
            
            # Update RFQ status
            rfq.status = 'QUOTED'
            rfq.save()
            
            messages.success(request, f'Quotation {quotation.quotation_number} created successfully!')
            return redirect('hiring:quotation_detail', pk=quotation.pk)
    else:
        # Pre-fill form with RFQ data
        initial_data = {
            'client': rfq.client,
            'hire_duration_days': rfq.hire_duration_days,
        }
        form = QuotationForm(initial=initial_data)
        
        # Pre-fill formset with RFQ items
        initial_items = []
        for rfq_item in rfq.items.all():
            material = rfq_item.material
            initial_items.append({
                'material': material,
                'quantity': rfq_item.quantity_requested,
                'daily_rate': material.daily_hire_rate,
                'duration_days': rfq.hire_duration_days,
            })
        
        formset = QuotationItemFormSet(initial=initial_items)
    
    context = {
        'form': form,
        'formset': formset,
        'rfq': rfq,
        'title': f'Create Quotation from RFQ {rfq.rfq_number}',
    }
    
    return render(request, 'hiring/quotation_form.html', context)

@login_required
def rfq_update(request, pk):
    """Update existing RFQ"""
    if not request.user.is_hce and not request.user.is_admin:
        messages.error(request, 'Only HCE or Administrators can update RFQs.')
        return redirect('hiring:rfq_detail', pk=pk)
    
    rfq = get_object_or_404(RequestForQuotation, pk=pk)
    
    if rfq.status != 'RECEIVED':
        messages.error(request, 'Only RFQs with status "RECEIVED" can be updated.')
        return redirect('hiring:rfq_detail', pk=rfq.pk)
    
    if request.method == 'POST':
        form = RFQForm(request.POST, instance=rfq)
        formset = RFQItemFormSet(request.POST, instance=rfq)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            
            messages.success(request, f'RFQ {rfq.rfq_number} updated successfully!')
            return redirect('hiring:rfq_detail', pk=rfq.pk)
    else:
        form = RFQForm(instance=rfq)
        formset = RFQItemFormSet(instance=rfq)
    
    context = {
        'form': form,
        'formset': formset,
        'rfq': rfq,
        'title': f'Update RFQ {rfq.rfq_number}',
    }
    
    return render(request, 'hiring/rfq_form.html', context)

@login_required
def rfq_delete(request, pk):
    """Delete RFQ"""
    if not request.user.is_admin:
        messages.error(request, 'Only Administrators can delete RFQs.')
        return redirect('hiring:rfq_detail', pk=pk)
    
    rfq = get_object_or_404(RequestForQuotation, pk=pk)
    
    if request.method == 'POST':
        rfq_number = rfq.rfq_number
        rfq.delete()
        messages.success(request, f'RFQ {rfq_number} deleted successfully!')
        return redirect('hiring:rfq_list')
    
    context = {
        'rfq': rfq,
    }
    
    return render(request, 'hiring/rfq_confirm_delete.html', context)

@login_required
def quotation_list(request):
    """List all quotations"""
    if not request.user.is_hce and not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'You do not have permission to view quotations.')
        return redirect('dashboard')
    
    quotations = Quotation.objects.all().order_by('-date_prepared')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        quotations = quotations.filter(status=status_filter)
    
    # Filter by client
    client_filter = request.GET.get('client', '')
    if client_filter:
        quotations = quotations.filter(client_id=client_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if date_from:
        quotations = quotations.filter(date_prepared__date__gte=date_from)
    if date_to:
        quotations = quotations.filter(date_prepared__date__lte=date_to)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        quotations = quotations.filter(
            Q(quotation_number__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # Show only own quotations for HCE (unless admin/fsm)
    if request.user.is_hce and not (request.user.is_fsm or request.user.is_admin):
        quotations = quotations.filter(prepared_by=request.user)
    
    # Pagination
    paginator = Paginator(quotations, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    clients = Client.objects.filter(is_active=True)
    
    context = {
        'quotations': page_obj,
        'status_filter': status_filter,
        'client_filter': client_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        'clients': clients,
        'status_choices': Quotation.STATUS_CHOICES,
    }
    
    return render(request, 'hiring/quotation_list.html', context)

@login_required
def quotation_create(request):
    """Create new quotation (without RFQ)"""
    if not request.user.is_hce and not request.user.is_admin:
        messages.error(request, 'Only HCE or Administrators can create quotations.')
        return redirect('hiring:quotation_list')
    
    if request.method == 'POST':
        form = QuotationForm(request.POST)
        formset = QuotationItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            quotation = form.save(commit=False)
            quotation.prepared_by = request.user
            quotation.valid_until = timezone.now().date() + timedelta(days=7)
            quotation.save()
            
            # Save items
            for item_form in formset:
                if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                    item = item_form.save(commit=False)
                    item.quotation = quotation
                    item.save()
            
            # Calculate totals
            quotation.calculate_totals()
            quotation.save()
            
            messages.success(request, f'Quotation {quotation.quotation_number} created successfully!')
            return redirect('hiring:quotation_detail', pk=quotation.pk)
    else:
        form = QuotationForm()
        formset = QuotationItemFormSet(queryset=QuotationItem.objects.none())
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'Create New Quotation',
    }
    
    return render(request, 'hiring/quotation_form.html', context)

@login_required
def quotation_detail(request, pk):
    """View quotation details"""
    if not request.user.is_hce and not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'You do not have permission to view quotation details.')
        return redirect('hiring:quotation_list')
    
    quotation = get_object_or_404(Quotation, pk=pk)
    
    # Check permissions for HCE
    if request.user.is_hce and not (request.user.is_fsm or request.user.is_admin):
        if quotation.prepared_by != request.user:
            messages.error(request, 'You can only view quotations you created.')
            return redirect('hiring:quotation_list')
    
    # Check if order already exists
    order_exists = HireOrder.objects.filter(quotation=quotation).exists()
    
    context = {
        'quotation': quotation,
        'order_exists': order_exists,
    }
    
    return render(request, 'hiring/quotation_detail.html', context)

@login_required
def quotation_approve(request, pk):
    """Approve quotation (FSM only)"""
    if not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'Only FSM or Administrators can approve quotations.')
        return redirect('hiring:quotation_detail', pk=pk)
    
    quotation = get_object_or_404(Quotation, pk=pk)
    
    if quotation.status != 'DRAFT':
        messages.warning(request, 'Only draft quotations can be approved.')
        return redirect('hiring:quotation_detail', pk=quotation.pk)
    
    quotation.status = 'SENT'
    quotation.approved_by = request.user
    quotation.save()
    
    messages.success(request, f'Quotation {quotation.quotation_number} approved and ready to send to client.')
    return redirect('hiring:quotation_detail', pk=quotation.pk)

@login_required
def quotation_send_to_client(request, pk):
    """Send quotation to client"""
    if not request.user.is_hce and not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'You do not have permission to send quotations.')
        return redirect('hiring:quotation_detail', pk=pk)
    
    quotation = get_object_or_404(Quotation, pk=pk)
    
    if quotation.status not in ['SENT', 'DRAFT']:
        messages.warning(request, 'Only draft or sent quotations can be sent to client.')
        return redirect('hiring:quotation_detail', pk=quotation.pk)
    
    # Generate PDF
    try:
        pdf_file = generate_quotation_pdf(quotation)
        
        # Update status
        quotation.status = 'SENT'
        quotation.save()
        
        # TODO: Implement email sending with PDF attachment
        # send_quotation_email(quotation, pdf_file)
        
        messages.success(request, f'Quotation {quotation.quotation_number} sent to client.')
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
    
    return redirect('hiring:quotation_detail', pk=quotation.pk)

@login_required
def quotation_accept(request, pk):
    """Mark quotation as accepted by client"""
    if not request.user.is_hce and not request.user.is_admin:
        messages.error(request, 'Only HCE or Administrators can accept quotations.')
        return redirect('hiring:quotation_detail', pk=pk)
    
    quotation = get_object_or_404(Quotation, pk=pk)
    
    if quotation.status != 'SENT':
        messages.warning(request, 'Only sent quotations can be accepted.')
        return redirect('hiring:quotation_detail', pk=quotation.pk)
    
    quotation.status = 'ACCEPTED'
    quotation.save()
    
    messages.success(request, f'Quotation {quotation.quotation_number} marked as accepted by client.')
    return redirect('hiring:create_order_from_quotation', quotation_pk=quotation.pk)

@login_required
def quotation_update(request, pk):
    """Update quotation"""
    if not request.user.is_hce and not request.user.is_admin:
        messages.error(request, 'Only HCE or Administrators can update quotations.')
        return redirect('hiring:quotation_detail', pk=pk)
    
    quotation = get_object_or_404(Quotation, pk=pk)
    
    if quotation.status not in ['DRAFT', 'SENT']:
        messages.error(request, 'Only draft or sent quotations can be updated.')
        return redirect('hiring:quotation_detail', pk=quotation.pk)
    
    # Check permissions for HCE
    if request.user.is_hce and not (request.user.is_fsm or request.user.is_admin):
        if quotation.prepared_by != request.user:
            messages.error(request, 'You can only update quotations you created.')
            return redirect('hiring:quotation_detail', pk=quotation.pk)
    
    if request.method == 'POST':
        form = QuotationForm(request.POST, instance=quotation)
        formset = QuotationItemFormSet(request.POST, instance=quotation)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            
            # Recalculate totals
            quotation.calculate_totals()
            quotation.save()
            
            messages.success(request, f'Quotation {quotation.quotation_number} updated successfully!')
            return redirect('hiring:quotation_detail', pk=quotation.pk)
    else:
        form = QuotationForm(instance=quotation)
        formset = QuotationItemFormSet(instance=quotation)
    
    context = {
        'form': form,
        'formset': formset,
        'quotation': quotation,
        'title': f'Update Quotation {quotation.quotation_number}',
    }
    
    return render(request, 'hiring/quotation_form.html', context)

@login_required
def quotation_delete(request, pk):
    """Delete quotation"""
    if not request.user.is_admin:
        messages.error(request, 'Only Administrators can delete quotations.')
        return redirect('hiring:quotation_detail', pk=pk)
    
    quotation = get_object_or_404(Quotation, pk=pk)
    
    if quotation.status not in ['DRAFT', 'REJECTED', 'EXPIRED']:
        messages.error(request, 'Only draft, rejected, or expired quotations can be deleted.')
        return redirect('hiring:quotation_detail', pk=quotation.pk)
    
    if request.method == 'POST':
        quotation_number = quotation.quotation_number
        quotation.delete()
        messages.success(request, f'Quotation {quotation_number} deleted successfully!')
        return redirect('hiring:quotation_list')
    
    context = {
        'quotation': quotation,
    }
    
    return render(request, 'hiring/quotation_confirm_delete.html', context)

@login_required
def create_order_from_quotation(request, quotation_pk):
    """Create order from accepted quotation"""
    if not request.user.is_hce and not request.user.is_admin:
        messages.error(request, 'Only HCE or Administrators can create orders.')
        return redirect('hiring:quotation_detail', pk=quotation_pk)
    
    quotation = get_object_or_404(Quotation, pk=quotation_pk)
    
    # Check if order already exists
    if HireOrder.objects.filter(quotation=quotation).exists():
        messages.warning(request, 'An order already exists for this quotation.')
        return redirect('hiring:quotation_detail', pk=quotation.pk)
    
    # Check if quotation is accepted
    if quotation.status != 'ACCEPTED':
        messages.warning(request, 'Please mark the quotation as accepted before creating an order.')
        return redirect('hiring:quotation_detail', pk=quotation.pk)
    
    # Check inventory availability
    for item in quotation.items.all():
        if item.material.available_quantity < item.quantity:
            messages.error(request, 
                f'Insufficient stock for {item.material.name}. '
                f'Available: {item.material.available_quantity}, Required: {item.quantity}'
            )
            return redirect('hiring:quotation_detail', pk=quotation.pk)
    
    if request.method == 'POST':
        form = HireOrderForm(request.POST)
        
        if form.is_valid():
            order = form.save(commit=False)
            order.quotation = quotation
            order.client = quotation.client
            order.created_by = request.user
            order.hire_duration_days = quotation.hire_duration_days
            order.save()
            
            # Create order items from quotation items
            for quotation_item in quotation.items.all():
                HireOrderItem.objects.create(
                    hire_order=order,
                    material=quotation_item.material,
                    quantity_ordered=quotation_item.quantity,
                )
            
            # Reserve inventory
            for item in order.items.all():
                material = item.material
                material.available_quantity -= item.quantity_ordered
                material.hired_quantity += item.quantity_ordered
                material.save()
            
            messages.success(request, f'Order {order.order_number} created successfully!')
            return redirect('hiring:order_detail', pk=order.pk)
    else:
        # Set expected return date (start date + hire duration)
        start_date = timezone.now().date() + timedelta(days=1)
        expected_return_date = start_date + timedelta(days=quotation.hire_duration_days)
        
        initial_data = {
            'start_date': start_date,
            'expected_return_date': expected_return_date,
        }
        
        form = HireOrderForm(initial=initial_data)
    
    context = {
        'form': form,
        'quotation': quotation,
        'title': f'Create Order from Quotation {quotation.quotation_number}',
    }
    
    return render(request, 'hiring/order_form.html', context)

@login_required
def order_list(request):
    """List all orders"""
    if not request.user.is_hce and not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'You do not have permission to view orders.')
        return redirect('dashboard')
    
    orders = HireOrder.objects.all().order_by('-order_date')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Filter by client
    client_filter = request.GET.get('client', '')
    if client_filter:
        orders = orders.filter(client_id=client_filter)
    
    # Filter by payment status
    payment_filter = request.GET.get('payment_status', '')
    if payment_filter:
        orders = orders.filter(payment_status=payment_filter)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(quotation__quotation_number__icontains=search_query)
        )
    
    # Show only own orders for HCE (unless admin/fsm)
    if request.user.is_hce and not (request.user.is_fsm or request.user.is_admin):
        orders = orders.filter(created_by=request.user)
    
    # Get overdue orders
    overdue_orders = HireOrder.objects.filter(
        status='ACTIVE',
        expected_return_date__lt=timezone.now().date()
    ).count()
    
    # Pagination
    paginator = Paginator(orders, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    clients = Client.objects.filter(is_active=True)
    
    context = {
        'orders': page_obj,
        'status_filter': status_filter,
        'client_filter': client_filter,
        'payment_filter': payment_filter,
        'search_query': search_query,
        'clients': clients,
        'status_choices': HireOrder.STATUS_CHOICES,
        'payment_status_choices': HireOrder.PAYMENT_STATUS_CHOICES,
        'overdue_orders': overdue_orders,
    }
    
    return render(request, 'hiring/order_list.html', context)

@login_required
def order_create(request):
    """Create new order (without quotation)"""
    if not request.user.is_hce and not request.user.is_admin:
        messages.error(request, 'Only HCE or Administrators can create orders.')
        return redirect('hiring:order_list')
    
    if request.method == 'POST':
        form = HireOrderForm(request.POST)
        formset = HireOrderItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            order = form.save(commit=False)
            order.created_by = request.user
            
            # Find or create client (you might want to change this logic)
            # For now, let's assume we need a client selection in the form
            # We'll add a client field to HireOrderForm
            
            order.save()
            
            # Save items
            for item_form in formset:
                if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                    item = item_form.save(commit=False)
                    item.hire_order = order
                    item.save()
                    
                    # Reserve inventory
                    material = item.material
                    material.available_quantity -= item.quantity_ordered
                    material.hired_quantity += item.quantity_ordered
                    material.save()
            
            messages.success(request, f'Order {order.order_number} created successfully!')
            return redirect('hiring:order_detail', pk=order.pk)
    else:
        form = HireOrderForm()
        formset = HireOrderItemFormSet(queryset=HireOrderItem.objects.none())
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'Create New Order',
    }
    
    return render(request, 'hiring/order_form.html', context)

@login_required
def order_detail(request, pk):
    """View order details"""
    if not request.user.is_hce and not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'You do not have permission to view order details.')
        return redirect('hiring:order_list')
    
    order = get_object_or_404(HireOrder, pk=pk)
    
    # Check permissions for HCE
    if request.user.is_hce and not (request.user.is_fsm or request.user.is_admin):
        if order.created_by != request.user:
            messages.error(request, 'You can only view orders you created.')
            return redirect('hiring:order_list')
    
    # Get related data
    lease_agreement = LeaseAgreement.objects.filter(hire_order=order).first()
    invoices = Invoice.objects.filter(hire_order=order)
    
    # Get deliveries (if delivery app is installed)
    try:
        from apps.delivery.models import Delivery
        deliveries = Delivery.objects.filter(hire_order=order)
    except ImportError:
        deliveries = []
    
    # Calculate days overdue
    days_overdue = order.days_overdue()
    
    # Calculate completion percentage
    total_items = order.items.count()
    dispatched_items = order.items.filter(quantity_dispatched__gte=F('quantity_ordered')).count()
    returned_items = order.items.filter(quantity_returned__gte=F('quantity_dispatched')).count()
    
    dispatch_percentage = (dispatched_items / total_items * 100) if total_items > 0 else 0
    return_percentage = (returned_items / total_items * 100) if total_items > 0 else 0
    
    context = {
        'order': order,
        'lease_agreement': lease_agreement,
        'invoices': invoices,
        'deliveries': deliveries,
        'days_overdue': days_overdue,
        'dispatch_percentage': dispatch_percentage,
        'return_percentage': return_percentage,
        'today': timezone.now().date(),
    }
    
    return render(request, 'hiring/order_detail.html', context)

@login_required
def order_update(request, pk):
    """Update order"""
    if not request.user.is_hce and not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'You do not have permission to update orders.')
        return redirect('hiring:order_detail', pk=pk)
    
    order = get_object_or_404(HireOrder, pk=pk)
    
    if order.status not in ['ORDERED', 'APPROVED']:
        messages.error(request, 'Only ordered or approved orders can be updated.')
        return redirect('hiring:order_detail', pk=order.pk)
    
    # Check permissions for HCE
    if request.user.is_hce and not (request.user.is_fsm or request.user.is_admin):
        if order.created_by != request.user:
            messages.error(request, 'You can only update orders you created.')
            return redirect('hiring:order_detail', pk=order.pk)
    
    if request.method == 'POST':
        form = HireOrderForm(request.POST, instance=order)
        formset = HireOrderItemFormSet(request.POST, instance=order)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            
            messages.success(request, f'Order {order.order_number} updated successfully!')
            return redirect('hiring:order_detail', pk=order.pk)
    else:
        form = HireOrderForm(instance=order)
        formset = HireOrderItemFormSet(instance=order)
    
    context = {
        'form': form,
        'formset': formset,
        'order': order,
        'title': f'Update Order {order.order_number}',
    }
    
    return render(request, 'hiring/order_form.html', context)

@login_required
def order_update_status(request, pk, status):
    """Update order status"""
    if not request.user.is_hce and not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'You do not have permission to update order status.')
        return redirect('hiring:order_detail', pk=pk)
    
    order = get_object_or_404(HireOrder, pk=pk)
    
    # Validate status transition
    valid_transitions = {
        'ORDERED': ['APPROVED', 'CANCELLED'],
        'APPROVED': ['DISPATCHED', 'CANCELLED'],
        'DISPATCHED': ['ACTIVE'],
        'ACTIVE': ['RETURNED'],
        'RETURNED': ['COMPLETED'],
    }
    
    current_status = order.status
    if status not in valid_transitions.get(current_status, []):
        messages.error(request, f'Cannot change status from {current_status} to {status}.')
        return redirect('hiring:order_detail', pk=order.pk)
    
    order.status = status
    
    # Handle special status changes
    if status == 'RETURNED':
        order.actual_return_date = timezone.now().date()
        
        # Release inventory when returned
        for item in order.items.all():
            material = item.material
            material.hired_quantity -= item.quantity_dispatched
            material.available_quantity += item.quantity_returned
            material.save()
            
    elif status == 'COMPLETED':
        # Release any remaining reserved inventory
        for item in order.items.all():
            material = item.material
            if item.quantity_dispatched > item.quantity_returned:
                material.hired_quantity -= (item.quantity_dispatched - item.quantity_returned)
                material.save()
    
    order.save()
    
    messages.success(request, f'Order {order.order_number} status updated to {status}.')
    return redirect('hiring:order_detail', pk=order.pk)

@login_required
def create_lease_agreement(request, order_pk):
    """Create lease agreement for order"""
    if not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'Only FSM or Administrators can create lease agreements.')
        return redirect('hiring:order_detail', pk=order_pk)
    
    order = get_object_or_404(HireOrder, pk=order_pk)
    
    # Check if lease agreement already exists
    if LeaseAgreement.objects.filter(hire_order=order).exists():
        messages.warning(request, 'A lease agreement already exists for this order.')
        return redirect('hiring:order_detail', pk=order.pk)
    
    if request.method == 'POST':
        form = LeaseAgreementForm(request.POST)
        
        if form.is_valid():
            lease = form.save(commit=False)
            lease.hire_order = order
            lease.client = order.client
            lease.start_date = order.start_date
            lease.end_date = order.expected_return_date
            lease.hire_duration_days = order.hire_duration_days
            lease.signed_by_fsm = request.user
            lease.fsm_signature_date = timezone.now().date()
            lease.save()
            
            messages.success(request, f'Lease agreement {lease.agreement_number} created successfully!')
            
            # Generate PDF
            try:
                pdf_file = generate_lease_agreement_pdf(lease)
                # TODO: Save PDF to lease.agreement_document
            except Exception as e:
                messages.warning(request, f'PDF generation failed: {str(e)}')
            
            return redirect('hiring:order_detail', pk=order.pk)
    else:
        # Set default terms and conditions for Zimbabwe
        default_terms = """
        TERMS AND CONDITIONS OF HIRE - FOSSIL CONTRACTING
        
        1. HIRE PERIOD
        The hire period commences from the date of dispatch and continues until all equipment is returned to our yard.
        
        2. RESPONSIBILITIES
        2.1 The Hirer shall:
            a) Be responsible for the safe custody and return of all hired equipment in good condition
            b) Ensure equipment is used in accordance with safety regulations and manufacturer guidelines
            c) Not make any alterations or repairs to the equipment without written consent
        
        3. LATE RETURNS
        3.1 Equipment must be returned by the agreed date
        3.2 Late returns will incur penalties at the daily hire rate plus 25% administration fee
        
        4. DAMAGE AND LOSS
        4.1 The Hirer is responsible for any loss or damage to equipment during hire period
        4.2 Damage will be assessed based on replacement cost
        4.3 Lost equipment must be paid for at current replacement value
        
        5. PAYMENT TERMS
        5.1 100% advance payment required before dispatch
        5.2 Payment by bank transfer to:
            Bank: CBZ Bank
            Account: Fossil Contracting
            Account Number: 456789123456
            Branch: Harare Main
        5.3 All prices exclude 15% VAT
        
        6. JURISDICTION
        6.1 This agreement shall be governed by Zimbabwean law
        6.2 Any disputes shall be settled in Harare courts
        
        By signing below, the Hirer acknowledges and agrees to all terms and conditions.
        """
        
        initial_data = {
            'late_return_penalty_per_day': 50.00,
            'damage_assessment_policy': 'Damage will be assessed by our technical team based on replacement cost of damaged items. The Hirer will be liable for repair or replacement costs.',
            'terms_and_conditions': default_terms,
        }
        
        form = LeaseAgreementForm(initial=initial_data)
    
    context = {
        'form': form,
        'order': order,
        'title': f'Create Lease Agreement for Order {order.order_number}',
    }
    
    return render(request, 'hiring/lease_agreement_form.html', context)

@login_required
def lease_list(request):
    """List all lease agreements"""
    if not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'Only FSM or Administrators can view lease agreements.')
        return redirect('dashboard')
    
    leases = LeaseAgreement.objects.all().order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        leases = leases.filter(status=status_filter)
    
    # Filter by client
    client_filter = request.GET.get('client', '')
    if client_filter:
        leases = leases.filter(client_id=client_filter)
    
    # Filter signed status
    signed_filter = request.GET.get('signed', '')
    if signed_filter == 'signed':
        leases = leases.filter(signed_by_client=True, signed_by_fsm__isnull=False)
    elif signed_filter == 'unsigned':
        leases = leases.filter(Q(signed_by_client=False) | Q(signed_by_fsm__isnull=True))
    
    # Pagination
    paginator = Paginator(leases, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    clients = Client.objects.filter(is_active=True)
    
    context = {
        'leases': page_obj,
        'status_filter': status_filter,
        'client_filter': client_filter,
        'signed_filter': signed_filter,
        'clients': clients,
        'status_choices': LeaseAgreement.STATUS_CHOICES,
    }
    
    return render(request, 'hiring/lease_list.html', context)

@login_required
def lease_detail(request, pk):
    """View lease agreement details"""
    if not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'Only FSM or Administrators can view lease agreements.')
        return redirect('hiring:lease_list')
    
    lease = get_object_or_404(LeaseAgreement, pk=pk)
    
    context = {
        'lease': lease,
    }
    
    return render(request, 'hiring/lease_detail.html', context)

@login_required
def lease_sign_fsm(request, pk):
    """FSM signs the lease agreement"""
    if not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'Only FSM or Administrators can sign lease agreements.')
        return redirect('hiring:lease_detail', pk=pk)
    
    lease = get_object_or_404(LeaseAgreement, pk=pk)
    
    if lease.signed_by_fsm:
        messages.warning(request, 'FSM has already signed this lease agreement.')
        return redirect('hiring:lease_detail', pk=lease.pk)
    
    lease.signed_by_fsm = request.user
    lease.fsm_signature_date = timezone.now().date()
    
    if lease.signed_by_client:
        lease.status = 'ACTIVE'
    
    lease.save()
    
    messages.success(request, 'Lease agreement signed by FSM.')
    return redirect('hiring:lease_detail', pk=lease.pk)

@login_required
def lease_sign_client(request, pk):
    """Mark lease as signed by client"""
    if not request.user.is_hce and not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'You do not have permission to mark lease as signed by client.')
        return redirect('hiring:lease_detail', pk=pk)
    
    lease = get_object_or_404(LeaseAgreement, pk=pk)
    
    if lease.signed_by_client:
        messages.warning(request, 'Client has already signed this lease agreement.')
        return redirect('hiring:lease_detail', pk=lease.pk)
    
    lease.signed_by_client = True
    lease.client_signature_date = timezone.now().date()
    
    if lease.signed_by_fsm:
        lease.status = 'ACTIVE'
    
    lease.save()
    
    messages.success(request, 'Lease agreement marked as signed by client.')
    return redirect('hiring:lease_detail', pk=lease.pk)

@login_required
def lease_download(request, pk):
    """Download lease agreement PDF"""
    if not request.user.is_hce and not request.user.is_fsm and not request.user.is_admin:
        messages.error(request, 'You do not have permission to download lease agreements.')
        return redirect('hiring:lease_detail', pk=pk)
    
    lease = get_object_or_404(LeaseAgreement, pk=pk)
    
    try:
        # Generate PDF
        response = generate_lease_agreement_pdf(lease)
        return response
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('hiring:lease_detail', pk=lease.pk)

# AJAX Views
@login_required
def get_material_rate(request, material_id):
    """Get daily rate for material (AJAX)"""
    try:
        material = Material.objects.get(pk=material_id)
        return JsonResponse({
            'success': True,
            'daily_rate': str(material.daily_hire_rate),
            'available_quantity': material.available_quantity
        })
    except Material.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Material not found'})

@login_required
def check_inventory_availability(request):
    """Check inventory availability for materials (AJAX)"""
    material_ids = request.GET.getlist('material_ids[]')
    quantities = request.GET.getlist('quantities[]')
    
    if len(material_ids) != len(quantities):
        return JsonResponse({'success': False, 'error': 'Invalid request'})
    
    results = []
    all_available = True
    
    for i in range(len(material_ids)):
        try:
            material = Material.objects.get(pk=material_ids[i])
            quantity_needed = int(quantities[i])
            available = material.available_quantity >= quantity_needed
            
            results.append({
                'material_id': material.id,
                'material_name': material.name,
                'needed': quantity_needed,
                'available': material.available_quantity,
                'is_available': available
            })
            
            if not available:
                all_available = False
                
        except (Material.DoesNotExist, ValueError):
            return JsonResponse({'success': False, 'error': 'Invalid material or quantity'})
    
    return JsonResponse({
        'success': True,
        'all_available': all_available,
        'results': results
    })