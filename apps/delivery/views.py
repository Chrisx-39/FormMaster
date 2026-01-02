from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.forms import inlineformset_factory
import json
from .models import *
from .forms import *
from apps.hiring.models import HireOrder

class TransportRequestListView(LoginRequiredMixin, ListView):
    model = TransportRequest
    template_name = 'delivery/transport_list.html'
    context_object_name = 'requests'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = TransportRequest.objects.all().order_by('-request_date')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by order
        order = self.request.GET.get('order')
        if order:
            queryset = queryset.filter(hire_order__order_number__icontains=order)
        
        # Filter by date
        date = self.request.GET.get('date')
        if date:
            queryset = queryset.filter(required_date=date)
        
        # Filter by request number
        request_number = self.request.GET.get('request_number')
        if request_number:
            queryset = queryset.filter(request_number__icontains=request_number)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = TransportRequest.STATUS_CHOICES
        return context

class TransportRequestDetailView(LoginRequiredMixin, DetailView):
    model = TransportRequest
    template_name = 'delivery/transport_detail.html'
    context_object_name = 'request'

class TransportRequestCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = TransportRequest
    template_name = 'delivery/transport_create.html'
    form_class = TransportRequestForm
    
    def test_func(self):
        return self.request.user.is_hce() or self.request.user.is_admin()
    
    def get_initial(self):
        initial = super().get_initial()
        order_id = self.request.GET.get('order_id')
        if order_id:
            order = get_object_or_404(HireOrder, pk=order_id)
            initial.update({
                'hire_order': order,
                'delivery_address': order.client.address,
                'required_date': timezone.now().date(),
            })
        return initial
    
    def form_valid(self, form):
        form.instance.requested_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Transport request {form.instance.request_number} created successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('delivery:transport_detail', kwargs={'pk': self.object.pk})

class TransportRequestApproveView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = TransportRequest
    form_class = TransportRequestApproveForm
    template_name = 'delivery/transport_approve.html'
    
    def test_func(self):
        return self.request.user.is_fsm() or self.request.user.is_admin()
    
    def form_valid(self, form):
        form.instance.approved_by = self.request.user
        form.instance.status = 'APPROVED'
        response = super().form_valid(form)
        messages.success(self.request, f'Transport request {self.object.request_number} approved successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('delivery:transport_detail', kwargs={'pk': self.object.pk})

class TransportRequestUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = TransportRequest
    form_class = TransportRequestForm
    template_name = 'delivery/transport_update.html'
    
    def test_func(self):
        return self.request.user.is_hce() or self.request.user.is_fsm() or self.request.user.is_admin()
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Transport request {self.object.request_number} updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('delivery:transport_detail', kwargs={'pk': self.object.pk})

class TransportRequestCancelView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_hce() or self.request.user.is_fsm() or self.request.user.is_admin()
    
    def post(self, request, pk):
        transport_request = get_object_or_404(TransportRequest, pk=pk)
        if transport_request.status == 'PENDING' or transport_request.status == 'APPROVED':
            transport_request.status = 'CANCELLED'
            transport_request.save()
            messages.success(request, f'Transport request {transport_request.request_number} cancelled successfully!')
        else:
            messages.error(request, 'Cannot cancel a request in its current status.')
        
        return redirect('delivery:transport_detail', pk=pk)

class DeliveryListView(LoginRequiredMixin, ListView):
    model = Delivery
    template_name = 'delivery/delivery_list.html'
    context_object_name = 'deliveries'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Delivery.objects.all().order_by('-departure_time')
        
        # Filter by type
        delivery_type = self.request.GET.get('type')
        if delivery_type:
            queryset = queryset.filter(delivery_type=delivery_type)
        
        # Filter by order
        order = self.request.GET.get('order')
        if order:
            queryset = queryset.filter(hire_order__order_number__icontains=order)
        
        # Filter by date
        date = self.request.GET.get('date')
        if date:
            queryset = queryset.filter(departure_time__date=date)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by delivery number
        delivery_number = self.request.GET.get('delivery_number')
        if delivery_number:
            queryset = queryset.filter(delivery_number__icontains=delivery_number)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delivery_type_choices'] = Delivery.DELIVERY_TYPE_CHOICES
        context['status_choices'] = Delivery.STATUS_CHOICES
        return context

class DeliveryDetailView(LoginRequiredMixin, DetailView):
    model = Delivery
    template_name = 'delivery/delivery_detail.html'
    context_object_name = 'delivery'

class DeliveryCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Delivery
    template_name = 'delivery/delivery_create.html'
    form_class = DeliveryForm
    
    def test_func(self):
        return self.request.user.is_hce() or self.request.user.is_scaffolder() or self.request.user.is_admin()
    
    def get_initial(self):
        initial = super().get_initial()
        order_id = self.request.GET.get('order_id')
        if order_id:
            order = get_object_or_404(HireOrder, pk=order_id)
            transport_request = TransportRequest.objects.filter(hire_order=order, status='APPROVED').first()
            initial.update({
                'hire_order': order,
                'transport_request': transport_request,
                'departure_time': timezone.now(),
                'delivery_address': order.client.address if order.client else '',
                'delivery_type': 'OUTGOING',
            })
        return initial
    
    def form_valid(self, form):
        form.instance.inspected_by = self.request.user
        response = super().form_valid(form)
        
        # Create delivery note
        delivery_note = DeliveryNote.objects.create(delivery=form.instance)
        
        # Add delivery note items
        for order_item in form.instance.hire_order.items.all():
            DeliveryNoteItem.objects.create(
                delivery_note=delivery_note,
                material=order_item.material,
                quantity=order_item.quantity_ordered
            )
        
        messages.success(self.request, f'Delivery {form.instance.delivery_number} created successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('delivery:delivery_detail', kwargs={'pk': self.object.pk})

class DeliveryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Delivery
    form_class = DeliveryForm
    template_name = 'delivery/delivery_update.html'
    
    def test_func(self):
        return self.request.user.is_hce() or self.request.user.is_scaffolder() or self.request.user.is_admin()
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Delivery {self.object.delivery_number} updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('delivery:delivery_detail', kwargs={'pk': self.object.pk})

class DeliveryMarkAsDeliveredView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_hce() or self.request.user.is_scaffolder() or self.request.user.is_admin()
    
    def post(self, request, pk):
        delivery = get_object_or_404(Delivery, pk=pk)
        delivery.mark_as_delivered()
        messages.success(request, f'Delivery {delivery.delivery_number} marked as delivered!')
        return redirect('delivery:delivery_detail', pk=pk)

class DeliveryNoteDetailView(LoginRequiredMixin, DetailView):
    model = DeliveryNote
    template_name = 'delivery/delivery_note_detail.html'
    context_object_name = 'delivery_note'

class DeliveryNoteUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = DeliveryNote
    form_class = DeliveryNoteForm
    template_name = 'delivery/delivery_note_update.html'
    
    def test_func(self):
        return self.request.user.is_hce() or self.request.user.is_scaffolder() or self.request.user.is_admin()
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Delivery note {self.object.note_number} updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('delivery:delivery_note_detail', kwargs={'pk': self.object.pk})

class DeliveryNoteItemsUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'delivery/delivery_note_items_update.html'
    
    def test_func(self):
        return self.request.user.is_hce() or self.request.user.is_scaffolder() or self.request.user.is_admin()
    
    def get(self, request, pk):
        delivery_note = get_object_or_404(DeliveryNote, pk=pk)
        formset = DeliveryNoteItemFormSet(instance=delivery_note)
        return render(request, self.template_name, {
            'delivery_note': delivery_note,
            'formset': formset,
        })
    
    def post(self, request, pk):
        delivery_note = get_object_or_404(DeliveryNote, pk=pk)
        formset = DeliveryNoteItemFormSet(request.POST, instance=delivery_note)
        
        if formset.is_valid():
            formset.save()
            messages.success(request, f'Delivery note items updated successfully!')
            return redirect('delivery:delivery_note_detail', pk=pk)
        
        return render(request, self.template_name, {
            'delivery_note': delivery_note,
            'formset': formset,
        })

def sign_delivery_note(request, pk, role):
    """Sign delivery note by different roles"""
    delivery_note = get_object_or_404(DeliveryNote, pk=pk)
    
    if role == 'driver':
        delivery_note.signed_by_driver = True
        delivery_note.driver_signature_date = timezone.now()
    elif role == 'scaffolder':
        delivery_note.signed_by_scaffolder = True
        delivery_note.scaffolder_signature_date = timezone.now()
    elif role == 'security':
        delivery_note.signed_by_security = True
        delivery_note.security_signature_date = timezone.now()
    elif role == 'client':
        delivery_note.signed_by_client = True
        delivery_note.client_signature_date = timezone.now()
    
    delivery_note.save()
    
    messages.success(request, f'Delivery note signed as {role}!')
    return redirect('delivery:delivery_note_detail', pk=pk)

def generate_delivery_note_pdf(request, pk):
    """Generate PDF for delivery note"""
    delivery_note = get_object_or_404(DeliveryNote, pk=pk)
    
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="delivery_note_{delivery_note.note_number}.pdf"'
    
    # Create PDF
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    
    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(1*inch, height-1*inch, "DELIVERY NOTE")
    p.setFont("Helvetica", 10)
    p.drawString(1*inch, height-1.2*inch, f"Number: {delivery_note.note_number}")
    p.drawString(4*inch, height-1.2*inch, f"Date: {delivery_note.issued_date.date()}")
    
    # Delivery Info
    y = height - 1.6*inch
    p.drawString(1*inch, y, f"Order: {delivery_note.delivery.hire_order.order_number}")
    y -= 0.2*inch
    p.drawString(1*inch, y, f"Client: {delivery_note.delivery.hire_order.client.name}")
    y -= 0.2*inch
    p.drawString(1*inch, y, f"Delivery Address: {delivery_note.delivery.delivery_address}")
    y -= 0.2*inch
    p.drawString(1*inch, y, f"Driver: {delivery_note.delivery.driver_name}")
    y -= 0.2*inch
    p.drawString(1*inch, y, f"Truck: {delivery_note.delivery.truck_registration}")
    
    # Items table
    y = height - 3*inch
    p.setFont("Helvetica-Bold", 10)
    p.drawString(1*inch, y, "Material")
    p.drawString(4*inch, y, "Quantity")
    p.drawString(5*inch, y, "Condition")
    p.drawString(6*inch, y, "Notes")
    
    p.line(1*inch, y-0.1*inch, 7*inch, y-0.1*inch)
    y -= 0.2*inch
    
    p.setFont("Helvetica", 9)
    for item in delivery_note.items.all():
        p.drawString(1*inch, y, item.material.name[:25])
        p.drawString(4*inch, y, str(item.quantity))
        p.drawString(5*inch, y, item.get_condition_display())
        p.drawString(6*inch, y, item.notes[:15] if item.notes else "")
        y -= 0.2*inch
        
        if y < 1*inch:  # Start new page if running out of space
            p.showPage()
            y = height - 1*inch
    
    # Signatures
    y -= 0.4*inch
    p.setFont("Helvetica-Bold", 10)
    p.drawString(1*inch, y, "Signatures:")
    y -= 0.3*inch
    
    p.setFont("Helvetica", 9)
    p.drawString(1*inch, y, "Driver:")
    if delivery_note.signed_by_driver:
        p.drawString(2*inch, y, "✓ Signed")
        p.drawString(2.5*inch, y, f"Date: {delivery_note.driver_signature_date.date() if delivery_note.driver_signature_date else 'N/A'}")
    else:
        p.drawString(2*inch, y, "Pending")
    
    p.drawString(4*inch, y, "Scaffolder:")
    if delivery_note.signed_by_scaffolder:
        p.drawString(5.5*inch, y, "✓ Signed")
        p.drawString(6*inch, y, f"Date: {delivery_note.scaffolder_signature_date.date() if delivery_note.scaffolder_signature_date else 'N/A'}")
    else:
        p.drawString(5.5*inch, y, "Pending")
    y -= 0.2*inch
    
    p.drawString(1*inch, y, "Security:")
    if delivery_note.signed_by_security:
        p.drawString(2*inch, y, "✓ Signed")
        p.drawString(2.5*inch, y, f"Date: {delivery_note.security_signature_date.date() if delivery_note.security_signature_date else 'N/A'}")
    else:
        p.drawString(2*inch, y, "Pending")
    
    p.drawString(4*inch, y, "Client:")
    if delivery_note.signed_by_client:
        p.drawString(5.5*inch, y, "✓ Signed")
        p.drawString(6*inch, y, f"Date: {delivery_note.client_signature_date.date() if delivery_note.client_signature_date else 'N/A'}")
    else:
        p.drawString(5.5*inch, y, "Pending")
    
    p.showPage()
    p.save()
    
    return response

class GoodsReceivedVoucherListView(LoginRequiredMixin, ListView):
    model = GoodsReceivedVoucher
    template_name = 'delivery/grv_list.html'
    context_object_name = 'grvs'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = GoodsReceivedVoucher.objects.all().order_by('-received_date')
        
        # Filter by GRV number
        grv_number = self.request.GET.get('grv_number')
        if grv_number:
            queryset = queryset.filter(grv_number__icontains=grv_number)
        
        # Filter by order
        order = self.request.GET.get('order')
        if order:
            queryset = queryset.filter(hire_order__order_number__icontains=order)
        
        # Filter by date
        date = self.request.GET.get('date')
        if date:
            queryset = queryset.filter(received_date__date=date)
        
        return queryset

class GoodsReceivedVoucherDetailView(LoginRequiredMixin, DetailView):
    model = GoodsReceivedVoucher
    template_name = 'delivery/grv_detail.html'
    context_object_name = 'grv'

class GoodsReceivedVoucherCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = GoodsReceivedVoucher
    template_name = 'delivery/grv_create.html'
    form_class = GoodsReceivedVoucherForm
    
    def test_func(self):
        return self.request.user.is_hce() or self.request.user.is_admin()
    
    def get_initial(self):
        initial = super().get_initial()
        delivery_id = self.request.GET.get('delivery_id')
        if delivery_id:
            delivery = get_object_or_404(Delivery, pk=delivery_id)
            initial.update({
                'delivery': delivery,
                'hire_order': delivery.hire_order,
                'received_by': self.request.user,
            })
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = GRVItemFormSet(self.request.POST)
        else:
            delivery_id = self.request.GET.get('delivery_id')
            if delivery_id:
                delivery = get_object_or_404(Delivery, pk=delivery_id)
                # Pre-populate GRV items from delivery note
                delivery_note = delivery.deliverynote_set.first()
                initial_data = []
                if delivery_note:
                    for item in delivery_note.items.all():
                        initial_data.append({
                            'material': item.material,
                            'quantity_expected': item.quantity,
                            'quantity_received': item.quantity,
                            'condition_on_receipt': item.condition,
                        })
                
                formset = GRVItemFormSet(initial=initial_data)
                context['formset'] = formset
            else:
                context['formset'] = GRVItemFormSet()
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            
            messages.success(self.request, f'Goods Received Voucher {self.object.grv_number} created successfully!')
            return redirect('delivery:grv_detail', pk=self.object.pk)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class GoodsReceivedVoucherUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = GoodsReceivedVoucher
    form_class = GoodsReceivedVoucherForm
    template_name = 'delivery/grv_update.html'
    
    def test_func(self):
        return self.request.user.is_hce() or self.request.user.is_admin()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = GRVItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = GRVItemFormSet(instance=self.object)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            response = super().form_valid(form)
            formset.instance = self.object
            formset.save()
            
            messages.success(self.request, f'Goods Received Voucher {self.object.grv_number} updated successfully!')
            return response
        else:
            return self.render_to_response(self.get_context_data(form=form))
    
    def get_success_url(self):
        return reverse_lazy('delivery:grv_detail', kwargs={'pk': self.object.pk})

def generate_grv_pdf(request, pk):
    """Generate PDF for Goods Received Voucher"""
    grv = get_object_or_404(GoodsReceivedVoucher, pk=pk)
    
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="grv_{grv.grv_number}.pdf"'
    
    # Create PDF
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    
    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(1*inch, height-1*inch, "GOODS RECEIVED VOUCHER")
    p.setFont("Helvetica", 10)
    p.drawString(1*inch, height-1.2*inch, f"Number: {grv.grv_number}")
    p.drawString(4*inch, height-1.2*inch, f"Date: {grv.received_date.date()}")
    
    # Delivery Info
    y = height - 1.6*inch
    p.drawString(1*inch, y, f"Order: {grv.hire_order.order_number}")
    y -= 0.2*inch
    p.drawString(1*inch, y, f"Client: {grv.hire_order.client.name}")
    y -= 0.2*inch
    p.drawString(1*inch, y, f"Delivery: {grv.delivery.delivery_number}")
    y -= 0.2*inch
    p.drawString(1*inch, y, f"Received By: {grv.received_by.get_full_name()}")
    y -= 0.2*inch
    p.drawString(1*inch, y, f"All Items Received: {'Yes' if grv.all_items_received else 'No'}")
    
    if grv.discrepancy_notes:
        y -= 0.2*inch
        p.drawString(1*inch, y, f"Discrepancy Notes: {grv.discrepancy_notes[:50]}")
    
    # Items table
    y = height - 3*inch
    p.setFont("Helvetica-Bold", 10)
    p.drawString(1*inch, y, "Material")
    p.drawString(3*inch, y, "Expected")
    p.drawString(4*inch, y, "Received")
    p.drawString(5*inch, y, "Discrepancy")
    p.drawString(6*inch, y, "Condition")
    
    p.line(1*inch, y-0.1*inch, 7*inch, y-0.1*inch)
    y -= 0.2*inch
    
    p.setFont("Helvetica", 9)
    total_expected = 0
    total_received = 0
    for item in grv.items.all():
        p.drawString(1*inch, y, item.material.name[:20])
        p.drawString(3*inch, y, str(item.quantity_expected))
        p.drawString(4*inch, y, str(item.quantity_received))
        discrepancy = item.get_discrepancy()
        p.drawString(5*inch, y, str(discrepancy) if item.has_discrepancy() else "0")
        p.drawString(6*inch, y, item.get_condition_on_receipt_display())
        y -= 0.2*inch
        
        total_expected += item.quantity_expected
        total_received += item.quantity_received
        
        if y < 1*inch:
            p.showPage()
            y = height - 1*inch
    
    # Totals
    y -= 0.2*inch
    p.setFont("Helvetica-Bold", 10)
    p.drawString(1*inch, y, "Totals:")
    p.drawString(3*inch, y, str(total_expected))
    p.drawString(4*inch, y, str(total_received))
    p.drawString(5*inch, y, str(total_expected - total_received))
    
    # Signatures
    y -= 0.4*inch
    p.setFont("Helvetica-Bold", 10)
    p.drawString(1*inch, y, "Authorized Signature:")
    y -= 0.3*inch
    p.setFont("Helvetica", 9)
    p.line(1*inch, y, 3*inch, y)
    p.drawString(1*inch, y-0.2*inch, f"Name: {grv.received_by.get_full_name()}")
    p.drawString(1*inch, y-0.4*inch, f"Date: {grv.received_date.date()}")
    
    p.showPage()
    p.save()
    
    return response

def get_order_details(request, order_id):
    """Get order details for AJAX request"""
    order = get_object_or_404(HireOrder, pk=order_id)
    data = {
        'client_name': order.client.name if order.client else '',
        'address': order.client.address if order.client else '',
        'order_number': order.order_number,
    }
    return JsonResponse(data)

def get_delivery_note_items(request, delivery_id):
    """Get delivery note items for AJAX request"""
    delivery = get_object_or_404(Delivery, pk=delivery_id)
    delivery_note = delivery.deliverynote_set.first()
    items = []
    
    if delivery_note:
        for item in delivery_note.items.all():
            items.append({
                'material_id': item.material.id,
                'material_name': item.material.name,
                'quantity': item.quantity,
                'condition': item.condition,
            })
    
    return JsonResponse({'items': items})