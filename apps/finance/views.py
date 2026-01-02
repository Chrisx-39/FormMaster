from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
import json
from .models import *
from .forms import *
from apps.hiring.models import HireOrder

class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = 'finance/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Invoice.objects.all().order_by('-invoice_date')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(payment_status=status)
        
        # Filter by type
        invoice_type = self.request.GET.get('type')
        if invoice_type:
            queryset = queryset.filter(invoice_type=invoice_type)
        
        # Filter by client
        client = self.request.GET.get('client')
        if client:
            queryset = queryset.filter(client__name__icontains=client)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(invoice_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(invoice_date__lte=date_to)
        
        # Filter overdue invoices
        overdue = self.request.GET.get('overdue')
        if overdue:
            queryset = queryset.filter(due_date__lt=timezone.now().date(), payment_status__in=['PENDING', 'PARTIAL'])
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate summary
        total_outstanding = Invoice.objects.filter(
            payment_status__in=['PENDING', 'PARTIAL']
        ).aggregate(total=Sum('balance_due'))['total'] or 0
        
        total_overdue = Invoice.objects.filter(
            payment_status__in=['PENDING', 'PARTIAL'],
            due_date__lt=timezone.now().date()
        ).aggregate(total=Sum('balance_due'))['total'] or 0
        
        context.update({
            'total_outstanding': total_outstanding,
            'total_overdue': total_overdue,
            'payment_status_choices': Invoice.PAYMENT_STATUS_CHOICES,
            'invoice_type_choices': Invoice.INVOICE_TYPE_CHOICES,
        })
        return context

class InvoiceCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Invoice
    template_name = 'finance/invoice_create.html'
    form_class = InvoiceForm
    
    def test_func(self):
        return self.request.user.is_hce() or self.request.user.is_admin()
    
    def get_initial(self):
        initial = super().get_initial()
        order_id = self.request.GET.get('order_id')
        invoice_type = self.request.GET.get('type', 'ADVANCE')
        
        if order_id:
            order = get_object_or_404(HireOrder, pk=order_id)
            
            if invoice_type == 'ADVANCE':
                amount = order.get_total_amount()
            elif invoice_type == 'FINAL':
                # Calculate final amount including penalties
                amount = order.get_total_amount()
                penalty = order.calculate_late_penalty()
                amount += penalty
            else:
                amount = 0
            
            initial.update({
                'hire_order': order,
                'client': order.client,
                'invoice_type': invoice_type,
                'subtotal': amount,
                'tax_amount': amount * 0.15,
                'total_amount': amount * 1.15,
                'due_date': timezone.now().date() + timedelta(days=7),
            })
        return initial
    
    def form_valid(self, form):
        form.instance.issued_by = self.request.user
        response = super().form_valid(form)
        
        # Update order payment status
        order = form.instance.hire_order
        if form.instance.invoice_type == 'ADVANCE':
            order.payment_status = 'PARTIAL'
        elif form.instance.invoice_type == 'FINAL':
            order.payment_status = 'FULL'
        order.save()
        
        messages.success(self.request, f'Invoice {form.instance.invoice_number} created successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('finance:invoice_detail', kwargs={'pk': self.object.pk})

class PaymentCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Payment
    template_name = 'finance/payment_create.html'
    form_class = PaymentForm
    
    def test_func(self):
        return self.request.user.is_hce() or self.request.user.is_fsm() or self.request.user.is_admin()
    
    def get_initial(self):
        initial = super().get_initial()
        invoice_id = self.request.GET.get('invoice_id')
        
        if invoice_id:
            invoice = get_object_or_404(Invoice, pk=invoice_id)
            initial.update({
                'invoice': invoice,
                'payment_date': timezone.now().date(),
                'amount': invoice.balance_due,
            })
        return initial
    
    def form_valid(self, form):
        form.instance.received_by = self.request.user
        
        # Validate payment amount doesn't exceed balance
        if form.instance.amount > form.instance.invoice.balance_due:
            messages.error(self.request, 'Payment amount cannot exceed invoice balance!')
            return self.form_invalid(form)
        
        response = super().form_valid(form)
        
        # Update invoice status
        invoice = form.instance.invoice
        invoice.amount_paid += form.instance.amount
        invoice.balance_due = invoice.total_amount - invoice.amount_paid
        
        if invoice.balance_due <= 0:
            invoice.payment_status = 'PAID'
        elif invoice.amount_paid > 0:
            invoice.payment_status = 'PARTIAL'
        
        invoice.save()
        
        messages.success(self.request, f'Payment {form.instance.payment_number} recorded successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('finance:invoice_detail', kwargs={'pk': self.object.invoice.pk})

def revenue_dashboard(request):
    """Revenue dashboard for FSM and Admin"""
    if not request.user.is_fsm() and not request.user.is_admin():
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('core:dashboard')
    
    # Get date range
    period = request.GET.get('period', 'month')
    end_date = timezone.now().date()
    
    if period == 'week':
        start_date = end_date - timedelta(days=7)
        group_by = 'day'
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
        group_by = 'day'
    elif period == 'quarter':
        start_date = end_date - timedelta(days=90)
        group_by = 'week'
    else:  # year
        start_date = end_date - timedelta(days=365)
        group_by = 'month'
    
    # Get revenue data
    invoices = Invoice.objects.filter(
        invoice_date__range=[start_date, end_date],
        payment_status='PAID'
    )
    
    # Calculate metrics
    total_revenue = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
    total_invoices = invoices.count()
    avg_invoice_value = total_revenue / total_invoices if total_invoices > 0 else 0
    
    # Revenue by client
    revenue_by_client = invoices.values('client__name').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('-total')[:10]
    
    # Revenue by material category
    revenue_by_category = []
    # This would require joining with hire orders and materials
    
    # Payment method breakdown
    payment_methods = Payment.objects.filter(
        payment_date__range=[start_date, end_date]
    ).values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    # Aging report
    aging_report = {
        'current': Invoice.objects.filter(
            payment_status__in=['PENDING', 'PARTIAL'],
            due_date__gte=timezone.now().date()
        ).aggregate(total=Sum('balance_due'))['total'] or 0,
        '1_30': Invoice.objects.filter(
            payment_status__in=['PENDING', 'PARTIAL'],
            due_date__lt=timezone.now().date(),
            due_date__gte=timezone.now().date() - timedelta(days=30)
        ).aggregate(total=Sum('balance_due'))['total'] or 0,
        '31_60': Invoice.objects.filter(
            payment_status__in=['PENDING', 'PARTIAL'],
            due_date__lt=timezone.now().date() - timedelta(days=30),
            due_date__gte=timezone.now().date() - timedelta(days=60)
        ).aggregate(total=Sum('balance_due'))['total'] or 0,
        '61_90': Invoice.objects.filter(
            payment_status__in=['PENDING', 'PARTIAL'],
            due_date__lt=timezone.now().date() - timedelta(days=60),
            due_date__gte=timezone.now().date() - timedelta(days=90)
        ).aggregate(total=Sum('balance_due'))['total'] or 0,
        'over_90': Invoice.objects.filter(
            payment_status__in=['PENDING', 'PARTIAL'],
            due_date__lt=timezone.now().date() - timedelta(days=90)
        ).aggregate(total=Sum('balance_due'))['total'] or 0,
    }
    
    context = {
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'total_invoices': total_invoices,
        'avg_invoice_value': avg_invoice_value,
        'revenue_by_client': revenue_by_client,
        'revenue_by_category': revenue_by_category,
        'payment_methods': payment_methods,
        'aging_report': aging_report,
    }
    
    return render(request, 'finance/revenue_dashboard.html', context)

class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'finance/invoice_detail.html'
    context_object_name = 'invoice'


def generate_invoice_pdf(request, pk):
    """Generate PDF for invoice"""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
    
    # Create PDF
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    
    # Company Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(1*inch, height-1*inch, "Fossil Contracting")
    p.setFont("Helvetica", 12)
    p.drawString(1*inch, height-1.2*inch, "INVOICE")
    
    # Invoice Info
    p.setFont("Helvetica-Bold", 10)
    p.drawString(1*inch, height-1.6*inch, f"Invoice Number: {invoice.invoice_number}")
    p.drawString(4*inch, height-1.6*inch, f"Date: {invoice.invoice_date}")
    p.drawString(4*inch, height-1.8*inch, f"Due Date: {invoice.due_date}")
    
    # Client Info
    p.setFont("Helvetica-Bold", 10)
    p.drawString(1*inch, height-2.2*inch, "Bill To:")
    p.setFont("Helvetica", 9)
    p.drawString(1*inch, height-2.4*inch, invoice.client.name)
    p.drawString(1*inch, height-2.6*inch, invoice.client.address)
    p.drawString(1*inch, height-2.8*inch, f"Contact: {invoice.client.contact_person}")
    
    # Order Info
    p.setFont("Helvetica", 9)
    p.drawString(1*inch, height-3*inch, f"Order: {invoice.hire_order.order_number}")
    p.drawString(1*inch, height-3.2*inch, f"Invoice Type: {invoice.get_invoice_type_display()}")
    
    # Line items
    y = height - 3.8*inch
    p.setFont("Helvetica-Bold", 10)
    p.drawString(1*inch, y, "Description")
    p.drawString(4*inch, y, "Amount")
    
    p.line(1*inch, y-0.1*inch, 7*inch, y-0.1*inch)
    y -= 0.2*inch
    
    p.setFont("Helvetica", 9)
    p.drawString(1*inch, y, f"Rental Charges - Order {invoice.hire_order.order_number}")
    p.drawString(4*inch, y, f"${invoice.subtotal:.2f}")
    y -= 0.2*inch
    
    if invoice.invoice_type == 'FINAL':
        # Add penalty charges if any
        penalty = invoice.hire_order.calculate_late_penalty()
        if penalty > 0:
            p.drawString(1*inch, y, "Late Return Penalty")
            p.drawString(4*inch, y, f"${penalty:.2f}")
            y -= 0.2*inch
    
    # Totals
    y -= 0.2*inch
    p.line(1*inch, y, 7*inch, y)
    y -= 0.2*inch
    
    p.setFont("Helvetica", 9)
    p.drawString(3*inch, y, "Subtotal:")
    p.drawString(4*inch, y, f"${invoice.subtotal:.2f}")
    y -= 0.2*inch
    
    p.drawString(3*inch, y, "Tax (15%):")
    p.drawString(4*inch, y, f"${invoice.tax_amount:.2f}")
    y -= 0.2*inch
    
    p.setFont("Helvetica-Bold", 10)
    p.drawString(3*inch, y, "TOTAL:")
    p.drawString(4*inch, y, f"${invoice.total_amount:.2f}")
    y -= 0.2*inch
    
    p.drawString(3*inch, y, "Amount Paid:")
    p.drawString(4*inch, y, f"${invoice.amount_paid:.2f}")
    y -= 0.2*inch
    
    p.drawString(3*inch, y, "BALANCE DUE:")
    p.drawString(4*inch, y, f"${invoice.balance_due:.2f}")
    
    # Payment status
    y -= 0.4*inch
    p.setFont("Helvetica-Bold", 10)
    status_color = "green" if invoice.payment_status == 'PAID' else "red"
    p.setFillColor(status_color)
    p.drawString(1*inch, y, f"Payment Status: {invoice.get_payment_status_display()}")
    p.setFillColor("black")
    
    # Payment instructions
    y -= 0.3*inch
    p.setFont("Helvetica", 8)
    p.drawString(1*inch, y, "Payment Instructions:")
    y -= 0.15*inch
    p.drawString(1*inch, y, "Bank: Standard Chartered Bank")
    y -= 0.15*inch
    p.drawString(1*inch, y, "Account: 1234567890")
    y -= 0.15*inch
    p.drawString(1*inch, y, "Branch: Harare Main Branch")
    y -= 0.15*inch
    p.drawString(1*inch, y, "Reference: Please quote invoice number")
    
    p.showPage()
    p.save()
    
    return response