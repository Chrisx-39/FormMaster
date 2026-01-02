from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.db.models import Q, Count, Sum, Avg, F, ExpressionWrapper, DecimalField
from django.db.models.functions import ExtractYear, ExtractMonth
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import *
from .forms import *
from apps.hiring.models import HireOrder
from apps.finance.models import Invoice, Payment

class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Client.objects.all().order_by('name')
        
        # Apply filters
        form = ClientSearchForm(self.request.GET)
        if form.is_valid():
            name = form.cleaned_data.get('name')
            client_type = form.cleaned_data.get('client_type')
            status = form.cleaned_data.get('status')
            city = form.cleaned_data.get('city')
            account_manager = form.cleaned_data.get('account_manager')
            date_from = form.cleaned_data.get('date_from')
            date_to = form.cleaned_data.get('date_to')
            credit_status = form.cleaned_data.get('credit_status')
            
            if name:
                queryset = queryset.filter(
                    Q(name__icontains=name) |
                    Q(trading_as__icontains=name) |
                    Q(client_number__icontains=name)
                )
            
            if client_type:
                queryset = queryset.filter(client_type=client_type)
            
            if status:
                queryset = queryset.filter(status=status)
            
            if city:
                queryset = queryset.filter(city__icontains=city)
            
            if account_manager:
                queryset = queryset.filter(account_manager=account_manager)
            
            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)
            
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)
            
            if credit_status:
                # Filter by credit utilization
                if credit_status == 'LOW':
                    queryset = queryset.filter(
                        current_balance__lt=F('credit_limit') * 0.5
                    )
                elif credit_status == 'MODERATE':
                    queryset = queryset.filter(
                        current_balance__gte=F('credit_limit') * 0.5,
                        current_balance__lt=F('credit_limit') * 0.75
                    )
                elif credit_status == 'HIGH':
                    queryset = queryset.filter(
                        current_balance__gte=F('credit_limit') * 0.75,
                        current_balance__lt=F('credit_limit') * 0.9
                    )
                elif credit_status == 'CRITICAL':
                    queryset = queryset.filter(
                        current_balance__gte=F('credit_limit') * 0.9
                    )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ClientSearchForm(self.request.GET)
        context['client_types'] = Client.CLIENT_TYPE_CHOICES
        context['client_statuses'] = Client.CLIENT_STATUS_CHOICES
        
        # Statistics
        context['total_clients'] = Client.objects.count()
        context['active_clients'] = Client.objects.filter(status='ACTIVE').count()
        context['total_credit_limit'] = Client.objects.aggregate(
            total=Sum('credit_limit')
        )['total'] or 0
        context['total_balance'] = Client.objects.aggregate(
            total=Sum('current_balance')
        )['total'] or 0
        
        return context

class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = 'clients/client_detail.html'
    context_object_name = 'client'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.object
        
        # Recent hire orders
        recent_orders = HireOrder.objects.filter(client=client).order_by('-order_date')[:10]
        
        # Recent invoices
        recent_invoices = Invoice.objects.filter(client=client).order_by('-invoice_date')[:10]
        
        # Recent payments
        recent_payments = Payment.objects.filter(invoice__client=client).order_by('-payment_date')[:10]
        
        # Financial summary
        total_orders = HireOrder.objects.filter(client=client).count()
        total_invoiced = Invoice.objects.filter(client=client).aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        total_paid = Payment.objects.filter(invoice__client=client).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        outstanding_balance = total_invoiced - total_paid
        
        # Rating history
        ratings = ClientRating.objects.filter(client=client).order_by('-rating_date')
        
        # Documents
        documents = client.documents.filter(is_active=True)
        
        # Notes
        notes = client.notes.filter(is_resolved=False).order_by('-created_at')
        
        # Contacts
        contacts = client.contacts.filter(is_active=True)
        
        # Sites
        sites = client.sites.filter(is_active=True)
        
        context.update({
            'recent_orders': recent_orders,
            'recent_invoices': recent_invoices,
            'recent_payments': recent_payments,
            'total_orders': total_orders,
            'total_invoiced': total_invoiced,
            'total_paid': total_paid,
            'outstanding_balance': outstanding_balance,
            'ratings': ratings,
            'documents': documents,
            'notes': notes,
            'contacts': contacts,
            'sites': sites,
            'note_form': ClientNoteForm(),
            'contact_form': ClientContactForm(),
            'site_form': ClientSiteForm(),
            'document_form': ClientDocumentForm(),
            'balance_form': BalanceUpdateForm(),
        })
        
        return context

class ClientCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    success_url = reverse_lazy('clients:client_list')
    
    def test_func(self):
        return self.request.user.is_hce() or self.request.user.is_fsm() or self.request.user.is_admin()
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        # Log the creation
        ClientHistory.objects.create(
            client=self.object,
            action='CREATED',
            performed_by=self.request.user,
            description=f'Client created by {self.request.user.get_full_name()}',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        
        messages.success(self.request, f'Client {self.object.name} created successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['contact_formset'] = ClientContactFormSet(self.request.POST)
            context['site_formset'] = ClientSiteFormSet(self.request.POST)
        else:
            context['contact_formset'] = ClientContactFormSet()
            context['site_formset'] = ClientSiteFormSet()
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        contact_formset = ClientContactFormSet(request.POST)
        site_formset = ClientSiteFormSet(request.POST)
        
        if form.is_valid() and contact_formset.is_valid() and site_formset.is_valid():
            return self.form_valid_all(form, contact_formset, site_formset)
        else:
            return self.form_invalid(form, contact_formset, site_formset)
    
    def form_valid_all(self, form, contact_formset, site_formset):
        self.object = form.save()
        contact_formset.instance = self.object
        contact_formset.save()
        site_formset.instance = self.object
        site_formset.save()
        
        # Log the creation
        ClientHistory.objects.create(
            client=self.object,
            action='CREATED',
            performed_by=self.request.user,
            description=f'Client created with {contact_formset.total_form_count()} contacts and {site_formset.total_form_count()} sites',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        
        messages.success(self.request, f'Client {self.object.name} created successfully!')
        return redirect(self.get_success_url())
    
    def form_invalid(self, form, contact_formset, site_formset):
        return self.render_to_response(
            self.get_context_data(
                form=form,
                contact_formset=contact_formset,
                site_formset=site_formset
            )
        )

class ClientUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    
    def test_func(self):
        return self.request.user.is_hce() or self.request.user.is_fsm() or self.request.user.is_admin()
    
    def get_success_url(self):
        return reverse_lazy('clients:client_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # Save old values before update
        old_instance = Client.objects.get(pk=self.object.pk)
        old_values = {
            'status': old_instance.status,
            'credit_limit': old_instance.credit_limit,
            'current_balance': old_instance.current_balance,
        }
        
        response = super().form_valid(form)
        
        # Check for changes and log them
        new_instance = self.object
        
        if old_instance.status != new_instance.status:
            ClientHistory.objects.create(
                client=new_instance,
                action='STATUS_CHANGE',
                performed_by=self.request.user,
                description=f'Status changed from {old_instance.status} to {new_instance.status}',
                old_value=old_instance.status,
                new_value=new_instance.status,
                ip_address=self.request.META.get('REMOTE_ADDR')
            )
        
        if old_instance.credit_limit != new_instance.credit_limit:
            ClientHistory.objects.create(
                client=new_instance,
                action='CREDIT_LIMIT_CHANGE',
                performed_by=self.request.user,
                description=f'Credit limit changed from {old_instance.credit_limit} to {new_instance.credit_limit}',
                old_value=str(old_instance.credit_limit),
                new_value=str(new_instance.credit_limit),
                ip_address=self.request.META.get('REMOTE_ADDR')
            )
        
        messages.success(self.request, f'Client {self.object.name} updated successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['contact_formset'] = ClientContactFormSet(self.request.POST, instance=self.object)
            context['site_formset'] = ClientSiteFormSet(self.request.POST, instance=self.object)
        else:
            context['contact_formset'] = ClientContactFormSet(instance=self.object)
            context['site_formset'] = ClientSiteFormSet(instance=self.object)
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        contact_formset = ClientContactFormSet(request.POST, instance=self.object)
        site_formset = ClientSiteFormSet(request.POST, instance=self.object)
        
        if form.is_valid() and contact_formset.is_valid() and site_formset.is_valid():
            return self.form_valid_all(form, contact_formset, site_formset)
        else:
            return self.form_invalid(form, contact_formset, site_formset)
    
    def form_valid_all(self, form, contact_formset, site_formset):
        self.object = form.save()
        contact_formset.instance = self.object
        contact_formset.save()
        site_formset.instance = self.object
        site_formset.save()
        
        messages.success(self.request, f'Client {self.object.name} updated successfully!')
        return redirect(self.get_success_url())
    
    def form_invalid(self, form, contact_formset, site_formset):
        return self.render_to_response(
            self.get_context_data(
                form=form,
                contact_formset=contact_formset,
                site_formset=site_formset
            )
        )

class ClientDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Client
    template_name = 'clients/client_confirm_delete.html'
    success_url = reverse_lazy('clients:client_list')
    
    def test_func(self):
        return self.request.user.is_admin()
    
    def delete(self, request, *args, **kwargs):
        client = self.get_object()
        messages.success(request, f'Client {client.name} deleted successfully!')
        return super().delete(request, *args, **kwargs)

class AddClientNoteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        form = ClientNoteForm(request.POST)
        
        if form.is_valid():
            note = form.save(commit=False)
            note.client = client
            note.created_by = request.user
            note.save()
            
            # Log the action
            ClientHistory.objects.create(
                client=client,
                action='NOTE_ADDED',
                performed_by=request.user,
                description=f'Note added: {note.subject}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Note added successfully!')
        else:
            messages.error(request, 'Error adding note. Please check the form.')
        
        return redirect('clients:client_detail', pk=pk)

class AddClientContactView(LoginRequiredMixin, View):
    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        form = ClientContactForm(request.POST)
        
        if form.is_valid():
            contact = form.save(commit=False)
            contact.client = client
            contact.save()
            
            # Log the action
            ClientHistory.objects.create(
                client=client,
                action='CONTACT_ADDED',
                performed_by=request.user,
                description=f'Contact added: {contact.name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Contact added successfully!')
        else:
            messages.error(request, 'Error adding contact. Please check the form.')
        
        return redirect('clients:client_detail', pk=pk)

class AddClientSiteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        form = ClientSiteForm(request.POST)
        
        if form.is_valid():
            site = form.save(commit=False)
            site.client = client
            site.save()
            
            # Log the action
            ClientHistory.objects.create(
                client=client,
                action='SITE_ADDED',
                performed_by=request.user,
                description=f'Site added: {site.site_name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Site added successfully!')
        else:
            messages.error(request, 'Error adding site. Please check the form.')
        
        return redirect('clients:client_detail', pk=pk)

class AddClientDocumentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        form = ClientDocumentForm(request.POST, request.FILES)
        
        if form.is_valid():
            document = form.save(commit=False)
            document.client = client
            document.uploaded_by = request.user
            document.save()
            
            # Log the action
            ClientHistory.objects.create(
                client=client,
                action='DOCUMENT_UPLOADED',
                performed_by=request.user,
                description=f'Document uploaded: {document.name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Document uploaded successfully!')
        else:
            messages.error(request, 'Error uploading document. Please check the form.')
        
        return redirect('clients:client_detail', pk=pk)

class UpdateClientBalanceView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_fsm() or self.request.user.is_admin()
    
    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        form = BalanceUpdateForm(request.POST)
        
        if form.is_valid():
            amount = form.cleaned_data['amount']
            transaction_type = form.cleaned_data['transaction_type']
            reason = form.cleaned_data['reason']
            reference = form.cleaned_data.get('reference_number', '')
            
            old_balance = client.current_balance
            
            if transaction_type == 'INCREASE':
                client.current_balance += amount
                action_description = f'Balance increased by {amount}'
            else:
                client.current_balance -= amount
                action_description = f'Balance decreased by {amount}'
            
            client.save()
            
            # Log the action
            ClientHistory.objects.create(
                client=client,
                action='BALANCE_UPDATE',
                performed_by=request.user,
                description=f'{action_description}: {reason}',
                old_value=str(old_balance),
                new_value=str(client.current_balance),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Client balance updated successfully! New balance: {client.current_balance}')
        else:
            messages.error(request, 'Error updating balance. Please check the form.')
        
        return redirect('clients:client_detail', pk=pk)

class MarkClientVerifiedView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_fsm() or self.request.user.is_admin()
    
    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        client.mark_as_verified()
        
        messages.success(request, f'Client {client.name} marked as verified!')
        return redirect('clients:client_detail', pk=pk)

class ClientCreditNotesView(LoginRequiredMixin, ListView):
    model = CreditNote
    template_name = 'clients/credit_notes.html'
    context_object_name = 'credit_notes'
    paginate_by = 20
    
    def get_queryset(self):
        self.client = get_object_or_404(Client, pk=self.kwargs['pk'])
        return CreditNote.objects.filter(client=self.client).order_by('-issued_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.client
        context['form'] = CreditNoteForm(initial={'client': self.client})
        return context

class CreateCreditNoteView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = CreditNote
    form_class = CreditNoteForm
    template_name = 'clients/credit_note_form.html'
    
    def test_func(self):
        return self.request.user.is_fsm() or self.request.user.is_admin()
    
    def get_initial(self):
        initial = super().get_initial()
        client_id = self.kwargs.get('pk')
        if client_id:
            client = get_object_or_404(Client, pk=client_id)
            initial['client'] = client
        return initial
    
    def form_valid(self, form):
        form.instance.issued_by = self.request.user
        response = super().form_valid(form)
        
        messages.success(self.request, f'Credit note {self.object.credit_note_number} created successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('clients:client_credit_notes', kwargs={'pk': self.object.client.pk})

class ApplyCreditNoteView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_fsm() or self.request.user.is_admin()
    
    def post(self, request, pk):
        credit_note = get_object_or_404(CreditNote, pk=pk)
        invoice_id = request.POST.get('invoice_id')
        
        if not invoice_id:
            messages.error(request, 'Please select an invoice to apply the credit note to.')
            return redirect('clients:client_credit_notes', pk=credit_note.client.pk)
        
        try:
            invoice = Invoice.objects.get(pk=invoice_id, client=credit_note.client)
            
            # Apply credit note
            credit_note.apply_to_invoice(invoice, request.user)
            
            messages.success(request, f'Credit note applied to invoice {invoice.invoice_number} successfully!')
        except Invoice.DoesNotExist:
            messages.error(request, 'Invalid invoice selected.')
        
        return redirect('clients:client_credit_notes', pk=credit_note.client.pk)

class ClientRatingsView(LoginRequiredMixin, ListView):
    model = ClientRating
    template_name = 'clients/ratings.html'
    context_object_name = 'ratings'
    paginate_by = 20
    
    def get_queryset(self):
        self.client = get_object_or_404(Client, pk=self.kwargs['pk'])
        return ClientRating.objects.filter(client=self.client).order_by('-rating_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.client
        context['form'] = ClientRatingForm()
        
        # Calculate average rating
        avg_rating = self.get_queryset().aggregate(
            avg=Avg('overall_score')
        )['avg'] or 0
        
        context['average_rating'] = avg_rating
        return context

class AddClientRatingView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ClientRating
    form_class = ClientRatingForm
    template_name = 'clients/rating_form.html'
    
    def test_func(self):
        return self.request.user.is_fsm() or self.request.user.is_admin()
    
    def get_initial(self):
        initial = super().get_initial()
        client_id = self.kwargs.get('pk')
        if client_id:
            client = get_object_or_404(Client, pk=client_id)
            initial['client'] = client
        return initial
    
    def form_valid(self, form):
        client = get_object_or_404(Client, pk=self.kwargs['pk'])
        form.instance.client = client
        form.instance.rated_by = self.request.user
        response = super().form_valid(form)
        
        messages.success(self.request, f'Rating added for {client.name} successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('clients:client_ratings', kwargs={'pk': self.object.client.pk})

class ClientDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'clients/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Overall statistics
        total_clients = Client.objects.count()
        active_clients = Client.objects.filter(status='ACTIVE').count()
        new_clients_month = Client.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Financial statistics
        financial_stats = Client.objects.aggregate(
            total_credit_limit=Sum('credit_limit'),
            total_balance=Sum('current_balance'),
            avg_credit_utilization=Avg(
                ExpressionWrapper(
                    F('current_balance') * 100.0 / F('credit_limit'),
                    output_field=DecimalField()
                )
            )
        )
        
        # Client type distribution
        client_type_dist = Client.objects.values('client_type').annotate(
            count=Count('id'),
            total_balance=Sum('current_balance')
        ).order_by('-count')
        
        # Top clients by balance
        top_clients_by_balance = Client.objects.filter(
            current_balance__gt=0
        ).order_by('-current_balance')[:10]
        
        # Clients by city
        clients_by_city = Client.objects.values('city').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Credit risk analysis
        credit_risk_stats = {
            'low': Client.objects.filter(
                current_balance__lt=F('credit_limit') * 0.5
            ).count(),
            'moderate': Client.objects.filter(
                current_balance__gte=F('credit_limit') * 0.5,
                current_balance__lt=F('credit_limit') * 0.75
            ).count(),
            'high': Client.objects.filter(
                current_balance__gte=F('credit_limit') * 0.75,
                current_balance__lt=F('credit_limit') * 0.9
            ).count(),
            'critical': Client.objects.filter(
                current_balance__gte=F('credit_limit') * 0.9
            ).count(),
        }
        
        # Recent activities
        recent_history = ClientHistory.objects.select_related('client', 'performed_by').order_by('-performed_at')[:10]
        
        # Expiring documents
        expiring_docs = ClientDocument.objects.filter(
            valid_until__gte=timezone.now().date(),
            valid_until__lte=timezone.now().date() + timedelta(days=30),
            is_active=True
        ).select_related('client').order_by('valid_until')[:10]
        
        # Follow-up notes
        follow_up_notes = ClientNote.objects.filter(
            follow_up_date__gte=timezone.now().date(),
            follow_up_date__lte=timezone.now().date() + timedelta(days=7),
            is_resolved=False
        ).select_related('client').order_by('follow_up_date')[:10]
        
        context.update({
            'total_clients': total_clients,
            'active_clients': active_clients,
            'new_clients_month': new_clients_month,
            'financial_stats': financial_stats,
            'client_type_dist': client_type_dist,
            'top_clients_by_balance': top_clients_by_balance,
            'clients_by_city': clients_by_city,
            'credit_risk_stats': credit_risk_stats,
            'recent_history': recent_history,
            'expiring_docs': expiring_docs,
            'follow_up_notes': follow_up_notes,
        })
        
        return context

class ClientReportsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'clients/reports.html'
    
    def test_func(self):
        return self.request.user.is_fsm() or self.request.user.is_admin()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Report parameters
        report_type = self.request.GET.get('type', 'summary')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        # Default date range (last 30 days)
        if not date_from:
            date_from = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not date_to:
            date_to = timezone.now().strftime('%Y-%m-%d')
        
        context['report_type'] = report_type
        context['date_from'] = date_from
        context['date_to'] = date_to
        
        # Generate report data based on type
        if report_type == 'summary':
            context['report_data'] = self.get_summary_report(date_from, date_to)
        elif report_type == 'credit':
            context['report_data'] = self.get_credit_report(date_from, date_to)
        elif report_type == 'activity':
            context['report_data'] = self.get_activity_report(date_from, date_to)
        elif report_type == 'geographic':
            context['report_data'] = self.get_geographic_report(date_from, date_to)
        
        return context
    
    def get_summary_report(self, date_from, date_to):
        """Generate summary report"""
        date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
        date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
        
        # New clients in period
        new_clients = Client.objects.filter(
            created_at__date__range=[date_from_dt, date_to_dt]
        ).count()
        
        # Status changes
        status_changes = ClientHistory.objects.filter(
            action='STATUS_CHANGE',
            performed_at__date__range=[date_from_dt, date_to_dt]
        ).count()
        
        # Balance updates
        balance_updates = ClientHistory.objects.filter(
            action='BALANCE_UPDATE',
            performed_at__date__range=[date_from_dt, date_to_dt]
        ).count()
        
        return {
            'new_clients': new_clients,
            'status_changes': status_changes,
            'balance_updates': balance_updates,
        }
    
    def get_credit_report(self, date_from, date_to):
        """Generate credit report"""
        date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
        date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
        
        # Clients with high credit utilization
        high_risk_clients = Client.objects.filter(
            current_balance__gte=F('credit_limit') * 0.75
        ).values('name', 'client_number', 'current_balance', 'credit_limit', 'credit_utilization')
        
        # Credit limit changes
        credit_changes = ClientHistory.objects.filter(
            action='CREDIT_LIMIT_CHANGE',
            performed_at__date__range=[date_from_dt, date_to_dt]
        ).select_related('client', 'performed_by')[:50]
        
        return {
            'high_risk_clients': high_risk_clients,
            'credit_changes': credit_changes,
        }
    
    def get_activity_report(self, date_from, date_to):
        """Generate activity report"""
        date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
        date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
        
        # Client activities
        activities = ClientHistory.objects.filter(
            performed_at__date__range=[date_from_dt, date_to_dt]
        ).select_related('client', 'performed_by').order_by('-performed_at')[:100]
        
        # Activity counts by type
        activity_counts = ClientHistory.objects.filter(
            performed_at__date__range=[date_from_dt, date_to_dt]
        ).values('action').annotate(count=Count('id')).order_by('-count')
        
        return {
            'activities': activities,
            'activity_counts': activity_counts,
        }
    
    def get_geographic_report(self, date_from, date_to):
        """Generate geographic report"""
        # Clients by city
        clients_by_city = Client.objects.values('city').annotate(
            count=Count('id'),
            total_balance=Sum('current_balance'),
            total_credit=Sum('credit_limit')
        ).order_by('-count')
        
        # Clients by province
        clients_by_province = Client.objects.values('province').annotate(
            count=Count('id'),
            total_balance=Sum('current_balance')
        ).order_by('-count')
        
        return {
            'clients_by_city': clients_by_city,
            'clients_by_province': clients_by_province,
        }

class ClientExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_fsm() or self.request.user.is_admin()
    
    def get(self, request):
        import csv
        from django.http import HttpResponse
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="clients_export.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Client Number', 'Name', 'Client Type', 'Status',
            'Contact Person', 'Email', 'Phone',
            'City', 'Province', 'Country',
            'Credit Limit', 'Current Balance', 'Available Credit',
            'Account Manager', 'Created Date'
        ])
        
        # Write data
        clients = Client.objects.all().select_related('account_manager')
        for client in clients:
            writer.writerow([
                client.client_number,
                client.name,
                client.get_client_type_display(),
                client.get_status_display(),
                client.contact_person,
                client.email,
                str(client.phone),
                client.city,
                client.province,
                str(client.country),
                client.credit_limit,
                client.current_balance,
                client.available_credit,
                client.account_manager.get_full_name() if client.account_manager else '',
                client.created_at.strftime('%Y-%m-%d')
            ])
        
        return response

class BlacklistClientView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_fsm()
    
    def get(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        form = BlacklistClientForm()
        
        return render(request, 'clients/blacklist_form.html', {
            'client': client,
            'form': form
        })
    
    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        form = BlacklistClientForm(request.POST, request.FILES)
        
        if form.is_valid():
            blacklist_entry = form.save(commit=False)
            blacklist_entry.client = client
            blacklist_entry.blacklisted_by = request.user
            blacklist_entry.save()
            
            # Log the action
            ClientHistory.objects.create(
                client=client,
                action='STATUS_CHANGE',
                performed_by=request.user,
                description=f'Client blacklisted: {form.cleaned_data["reason"].description}',
                old_value=client.status,
                new_value='BLACKLISTED',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Client {client.name} has been blacklisted.')
            return redirect('clients:client_detail', pk=pk)
        
        return render(request, 'clients/blacklist_form.html', {
            'client': client,
            'form': form
        })

class RemoveFromBlacklistView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_admin()
    
    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        
        # Remove from blacklist
        if hasattr(client, 'blacklist_entry'):
            client.blacklist_entry.delete()
        
        # Update client status
        client.status = 'ACTIVE'
        client.save()
        
        # Log the action
        ClientHistory.objects.create(
            client=client,
            action='STATUS_CHANGE',
            performed_by=request.user,
            description='Client removed from blacklist',
            old_value='BLACKLISTED',
            new_value='ACTIVE',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, f'Client {client.name} has been removed from blacklist.')
        return redirect('clients:client_detail', pk=pk)

# API Views
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
import json

@method_decorator(require_http_methods(["GET"]), name='dispatch')
class ClientAutocompleteView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '')
        clients = Client.objects.filter(
            Q(name__icontains=query) |
            Q(client_number__icontains=query) |
            Q(trading_as__icontains=query)
        ).filter(status='ACTIVE')[:10]
        
        results = []
        for client in clients:
            results.append({
                'id': client.pk,
                'text': f"{client.name} ({client.client_number})",
                'client_number': client.client_number,
                'name': client.name,
                'credit_limit': float(client.credit_limit),
                'available_credit': float(client.available_credit),
            })
        
        return JsonResponse({'results': results})

@method_decorator(require_http_methods(["GET"]), name='dispatch')
class ClientStatsView(LoginRequiredMixin, View):
    def get(self, request):
        stats = {
            'total': Client.objects.count(),
            'active': Client.objects.filter(status='ACTIVE').count(),
            'new_today': Client.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
            'new_week': Client.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
            'total_credit_limit': float(Client.objects.aggregate(
                total=Sum('credit_limit')
            )['total'] or 0),
            'total_balance': float(Client.objects.aggregate(
                total=Sum('current_balance')
            )['total'] or 0),
        }
        
        return JsonResponse(stats)

@require_http_methods(["POST"])
@login_required
def mark_note_resolved(request, pk):
    if not (request.user.is_hce() or request.user.is_fsm() or request.user.is_admin()):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        note = ClientNote.objects.get(pk=pk)
        note.mark_as_resolved(request.user, request.POST.get('resolution_notes', ''))
        
        return JsonResponse({'success': True, 'message': 'Note marked as resolved'})
    
    except ClientNote.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Note not found'}, status=404)

@require_http_methods(["POST"])
@login_required
def delete_document(request, pk):
    if not (request.user.is_hce() or request.user.is_fsm() or request.user.is_admin()):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        document = ClientDocument.objects.get(pk=pk)
        document.delete()
        
        return JsonResponse({'success': True, 'message': 'Document deleted successfully'})
    
    except ClientDocument.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Document not found'}, status=404)