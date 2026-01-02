from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, FileResponse
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
import io
import json
from datetime import datetime, timedelta

from .models import *
from .forms import *
from .utils import *
from apps.hiring.models import Quotation, RequestForQuotation, LeaseAgreement
from apps.finance.models import Invoice
from apps.delivery.models import DeliveryNote, GoodsReceivedVoucher

class DocumentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'documents/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get document statistics
        total_documents = GeneratedDocument.objects.count()
        today = timezone.now().date()
        
        # Recent documents
        recent_documents = GeneratedDocument.objects.order_by('-generated_at')[:10]
        
        # Document type distribution
        doc_types = GeneratedDocument.objects.values('document_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Monthly document generation
        month_start = today.replace(day=1)
        monthly_docs = GeneratedDocument.objects.filter(
            generated_at__gte=month_start
        ).count()
        
        # Documents by status
        status_counts = GeneratedDocument.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        context.update({
            'total_documents': total_documents,
            'monthly_documents': monthly_docs,
            'recent_documents': recent_documents,
            'document_types': doc_types,
            'status_counts': status_counts,
            'templates_count': DocumentTemplate.objects.count(),
            'pending_signatures': GeneratedDocument.objects.filter(status='SENT').count(),
        })
        
        return context

class DocumentListView(LoginRequiredMixin, ListView):
    model = GeneratedDocument
    template_name = 'documents/document_list.html'
    context_object_name = 'documents'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = GeneratedDocument.objects.all().order_by('-generated_at')
        
        # Apply filters
        form = DocumentSearchForm(self.request.GET)
        if form.is_valid():
            document_type = form.cleaned_data.get('document_type')
            status = form.cleaned_data.get('status')
            date_from = form.cleaned_data.get('date_from')
            date_to = form.cleaned_data.get('date_to')
            search = form.cleaned_data.get('search')
            
            if document_type:
                queryset = queryset.filter(document_type=document_type)
            
            if status:
                queryset = queryset.filter(status=status)
            
            if date_from:
                queryset = queryset.filter(generated_at__date__gte=date_from)
            
            if date_to:
                queryset = queryset.filter(generated_at__date__lte=date_to)
            
            if search:
                queryset = queryset.filter(
                    Q(document_number__icontains=search) |
                    Q(file_name__icontains=search) |
                    Q(sent_to_email__icontains=search) |
                    Q(generated_by__username__icontains=search) |
                    Q(generated_by__first_name__icontains=search) |
                    Q(generated_by__last_name__icontains=search)
                )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = DocumentSearchForm(self.request.GET)
        return context

class DocumentDetailView(LoginRequiredMixin, DetailView):
    model = GeneratedDocument
    template_name = 'documents/document_detail.html'
    context_object_name = 'document'
    
    def get(self, request, *args, **kwargs):
        # Log the view
        document = self.get_object()
        document.mark_as_viewed()
        
        # Create log entry
        DocumentLog.objects.create(
            document=document,
            action='VIEWED',
            performed_by=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return super().get(request, *args, **kwargs)

class DocumentDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        document = get_object_or_404(GeneratedDocument, pk=pk)
        
        if document.document_file:
            # Increment download count
            document.increment_download_count()
            
            # Create log entry
            DocumentLog.objects.create(
                document=document,
                action='DOWNLOADED',
                performed_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            response = FileResponse(document.document_file.open('rb'), 
                                   as_attachment=True,
                                   filename=document.file_name)
            return response
        else:
            messages.error(request, "Document file not found.")
            return redirect('documents:document_detail', pk=pk)

class DocumentPreviewView(LoginRequiredMixin, View):
    def get(self, request, pk):
        document = get_object_or_404(GeneratedDocument, pk=pk)
        
        if document.document_file and document.file_type == 'pdf':
            response = FileResponse(document.document_file.open('rb'), 
                                   content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{document.file_name}"'
            return response
        else:
            messages.error(request, "PDF preview not available.")
            return redirect('documents:document_detail', pk=pk)

class DocumentSendView(LoginRequiredMixin, View):
    def get(self, request, pk):
        document = get_object_or_404(GeneratedDocument, pk=pk)
        form = SendDocumentForm(initial={
            'subject': f"{document.get_document_type_display()} - {document.document_number}",
            'message': f"Please find attached {document.get_document_type_display().lower()} {document.document_number}."
        })
        
        return render(request, 'documents/document_send.html', {
            'document': document,
            'form': form
        })
    
    def post(self, request, pk):
        document = get_object_or_404(GeneratedDocument, pk=pk)
        form = SendDocumentForm(request.POST)
        
        if form.is_valid():
            try:
                # Send email with document
                recipient_email = form.cleaned_data['recipient_email']
                subject = form.cleaned_data['subject']
                message = form.cleaned_data['message']
                send_copy = form.cleaned_data['send_copy_to_sender']
                
                # TODO: Implement email sending
                # send_document_email(document, recipient_email, subject, message, send_copy)
                
                # Update document status
                document.mark_as_sent(email=recipient_email)
                
                # Create log entry
                DocumentLog.objects.create(
                    document=document,
                    action='SENT',
                    performed_by=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    notes=f"Sent to {recipient_email}"
                )
                
                messages.success(request, f"Document sent successfully to {recipient_email}")
                return redirect('documents:document_detail', pk=pk)
                
            except Exception as e:
                messages.error(request, f"Error sending document: {str(e)}")
        
        return render(request, 'documents/document_send.html', {
            'document': document,
            'form': form
        })

class GenerateDocumentView(LoginRequiredMixin, View):
    """Generic view to generate any type of document"""
    
    def get(self, request, doc_type, object_id):
        # Get the object based on type and ID
        if doc_type == 'quotation':
            obj = get_object_or_404(Quotation, pk=object_id)
            context = get_quotation_context(obj)
            template_name = 'quotation'
            file_name = f"Quotation_{obj.quotation_number}_{timezone.now().date()}.pdf"
            
        elif doc_type == 'invoice':
            obj = get_object_or_404(Invoice, pk=object_id)
            context = get_invoice_context(obj)
            template_name = 'invoice'
            file_name = f"Invoice_{obj.invoice_number}_{timezone.now().date()}.pdf"
            
        elif doc_type == 'lease_agreement':
            obj = get_object_or_404(LeaseAgreement, pk=object_id)
            context = get_lease_agreement_context(obj)
            template_name = 'lease_agreement'
            file_name = f"Lease_Agreement_{obj.agreement_number}_{timezone.now().date()}.pdf"
            
        elif doc_type == 'delivery_note':
            obj = get_object_or_404(DeliveryNote, pk=object_id)
            context = get_delivery_note_context(obj)
            template_name = 'delivery_note'
            file_name = f"Delivery_Note_{obj.note_number}_{timezone.now().date()}.pdf"
            
        elif doc_type == 'grv':
            obj = get_object_or_404(GoodsReceivedVoucher, pk=object_id)
            context = get_grv_context(obj)
            template_name = 'grv'
            file_name = f"GRV_{obj.grv_number}_{timezone.now().date()}.pdf"
            
        elif doc_type == 'rfq':
            obj = get_object_or_404(RequestForQuotation, pk=object_id)
            context = get_rfq_context(obj)
            template_name = 'rfq'
            file_name = f"RFQ_{obj.rfq_number}_{timezone.now().date()}.pdf"
            
        else:
            messages.error(request, "Invalid document type.")
            return redirect('dashboard')
        
        try:
            # Generate PDF
            pdf_buffer = generate_pdf_from_template(template_name, context)
            
            # Save generated document
            document = GeneratedDocument.objects.create(
                document_type=doc_type.upper(),
                generated_by=request.user,
                file_name=file_name,
                file_type='pdf',
                status='DRAFT'
            )
            
            # Link to appropriate object
            if doc_type == 'quotation':
                document.quotation = obj
            elif doc_type == 'invoice':
                document.invoice = obj
            elif doc_type == 'lease_agreement':
                document.lease_agreement = obj
            elif doc_type == 'delivery_note':
                document.delivery_note = obj
            elif doc_type == 'grv':
                document.goods_received_voucher = obj
            elif doc_type == 'rfq':
                document.request_for_quotation = obj
            
            # Save file
            document.document_file.save(file_name, ContentFile(pdf_buffer.getvalue()))
            document.save()
            
            # Create log entry
            DocumentLog.objects.create(
                document=document,
                action='GENERATED',
                performed_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f"{document.get_document_type_display()} generated successfully.")
            return redirect('documents:document_detail', pk=document.pk)
            
        except Exception as e:
            messages.error(request, f"Error generating document: {str(e)}")
            return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

class TemplateListView(LoginRequiredMixin, ListView):
    model = DocumentTemplate
    template_name = 'documents/template_list.html'
    context_object_name = 'templates'
    
    def get_queryset(self):
        return DocumentTemplate.objects.filter(is_active=True).order_by('document_type', 'name')

class TemplateCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = DocumentTemplate
    form_class = DocumentTemplateForm
    template_name = 'documents/template_form.html'
    success_url = reverse_lazy('documents:template_list')
    
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_fsm()
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Template created successfully.")
        return response

class TemplateUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = DocumentTemplate
    form_class = DocumentTemplateForm
    template_name = 'documents/template_form.html'
    success_url = reverse_lazy('documents:template_list')
    
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_fsm()
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Template updated successfully.")
        return response

class TemplatePreviewView(LoginRequiredMixin, UserPassesTestMixin, View):
    def get(self, request, pk):
        template = get_object_or_404(DocumentTemplate, pk=pk)
        
        # Generate sample context based on template type
        sample_context = get_sample_context(template.document_type)
        
        # Render template with sample data
        try:
            pdf_buffer = generate_pdf_from_template_html(
                template.html_template, 
                sample_context
            )
            
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="template_preview.pdf"'
            return response
            
        except Exception as e:
            messages.error(request, f"Error previewing template: {str(e)}")
            return redirect('documents:template_list')

class DocumentSettingsView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = DocumentSetting
    form_class = DocumentSettingForm
    template_name = 'documents/settings.html'
    success_url = reverse_lazy('documents:settings')
    
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_fsm()
    
    def get_object(self):
        # Get or create settings
        obj, created = DocumentSetting.objects.get_or_create(pk=1)
        return obj
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Settings updated successfully.")
        return response

class DocumentArchiveView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_fsm()
    
    def post(self, request, pk):
        document = get_object_or_404(GeneratedDocument, pk=pk)
        
        # Archive the document
        archived_doc = ArchivedDocument.objects.create(
            original_document=document,
            archived_by=request.user,
            archive_reason=request.POST.get('reason', '')
        )
        
        # Update original document status
        document.status = 'ARCHIVED'
        document.archived_at = timezone.now()
        document.save()
        
        # Create log entry
        DocumentLog.objects.create(
            document=document,
            action='ARCHIVED',
            performed_by=request.user,
            notes=request.POST.get('reason', '')
        )
        
        messages.success(request, "Document archived successfully.")
        return redirect('documents:document_detail', pk=pk)

class BulkDocumentActionView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_fsm()
    
    def post(self, request):
        form = BulkDocumentActionForm(request.POST)
        
        if form.is_valid():
            action = form.cleaned_data['action']
            document_ids = json.loads(form.cleaned_data['document_ids'])
            
            documents = GeneratedDocument.objects.filter(pk__in=document_ids)
            
            if action == 'archive':
                for document in documents:
                    ArchivedDocument.objects.create(
                        original_document=document,
                        archived_by=request.user,
                        archive_reason='Bulk archive'
                    )
                    document.status = 'ARCHIVED'
                    document.archived_at = timezone.now()
                    document.save()
                
                messages.success(request, f"{documents.count()} documents archived.")
                
            elif action == 'delete':
                count = documents.count()
                documents.delete()
                messages.success(request, f"{count} documents deleted.")
                
            elif action == 'send':
                # TODO: Implement bulk email sending
                messages.info(request, "Bulk email sending not implemented yet.")
            
            return redirect('documents:document_list')
        
        messages.error(request, "Invalid action.")
        return redirect('documents:document_list')

class DocumentStatsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'documents/stats.html'
    
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_fsm()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Date range (last 30 days)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Documents generated in last 30 days
        recent_docs = GeneratedDocument.objects.filter(
            generated_at__date__range=[start_date, end_date]
        )
        
        # Daily document count
        daily_counts = recent_docs.extra(
            select={'day': 'DATE(generated_at)'}
        ).values('day').annotate(count=Count('id')).order_by('day')
        
        # Document type distribution
        type_distribution = recent_docs.values('document_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Top generators
        top_generators = recent_docs.values(
            'generated_by__username', 
            'generated_by__first_name', 
            'generated_by__last_name'
        ).annotate(count=Count('id')).order_by('-count')[:10]
        
        # File size statistics
        total_size = GeneratedDocument.objects.aggregate(
            total=Sum('file_size')
        )['total'] or 0
        avg_size = GeneratedDocument.objects.aggregate(
            avg=Sum('file_size') / Count('id')
        )['avg'] or 0
        
        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'daily_counts': daily_counts,
            'type_distribution': type_distribution,
            'top_generators': top_generators,
            'total_documents': GeneratedDocument.objects.count(),
            'total_size_mb': total_size / (1024 * 1024),
            'avg_size_kb': avg_size / 1024,
            'archived_count': ArchivedDocument.objects.count(),
        })
        
        return context

# API Views for AJAX calls
@method_decorator(login_required, name='dispatch')
class GetDocumentCountsView(View):
    def get(self, request):
        counts = {
            'total': GeneratedDocument.objects.count(),
            'today': GeneratedDocument.objects.filter(
                generated_at__date=timezone.now().date()
            ).count(),
            'sent': GeneratedDocument.objects.filter(status='SENT').count(),
            'unsigned': GeneratedDocument.objects.filter(
                Q(status='SENT') | Q(status='VIEWED')
            ).count(),
        }
        return JsonResponse(counts)

@method_decorator(login_required, name='dispatch')
class GetRecentDocumentsView(View):
    def get(self, request):
        limit = int(request.GET.get('limit', 10))
        documents = GeneratedDocument.objects.order_by('-generated_at')[:limit]
        
        data = []
        for doc in documents:
            data.append({
                'id': doc.pk,
                'number': doc.document_number,
                'type': doc.get_document_type_display(),
                'status': doc.get_status_display(),
                'generated_at': doc.generated_at.strftime('%Y-%m-%d %H:%M'),
                'generated_by': doc.generated_by.get_full_name() or doc.generated_by.username,
                'url': doc.get_absolute_url(),
            })
        
        return JsonResponse({'documents': data})

@require_http_methods(["POST"])
@login_required
def delete_document(request, pk):
    if not (request.user.is_admin() or request.user.is_fsm()):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        document = GeneratedDocument.objects.get(pk=pk)
        
        # Create log before deletion
        DocumentLog.objects.create(
            document=document,
            action='DELETED',
            performed_by=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            notes=request.POST.get('reason', '')
        )
        
        # Delete the document
        document.delete()
        
        return JsonResponse({'success': True, 'message': 'Document deleted successfully'})
    
    except GeneratedDocument.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Document not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)