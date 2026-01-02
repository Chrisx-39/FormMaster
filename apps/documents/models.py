from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from apps.accounts.models import User
from apps.hiring.models import HireOrder, Quotation, RequestForQuotation
from apps.clients.models import Client
from apps.delivery.models import Delivery, DeliveryNote, GoodsReceivedVoucher

class DocumentTemplate(models.Model):
    """Base template for all document types"""
    DOCUMENT_TYPE_CHOICES = [
        ('QUOTATION', 'Quotation'),
        ('INVOICE', 'Invoice'),
        ('LEASE_AGREEMENT', 'Lease Agreement'),
        ('DELIVERY_NOTE', 'Delivery Note'),
        ('GOODS_RECEIVED_VOUCHER', 'Goods Received Voucher'),
        ('REQUEST_FOR_QUOTATION', 'Request for Quotation'),
        ('RECEIPT', 'Receipt'),
    ]
    
    name = models.CharField(max_length=200)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    template_file = models.FileField(upload_to='document_templates/', null=True, blank=True)
    html_template = models.TextField(blank=True, help_text="HTML template with variables like {{client.name}}")
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['document_type', 'name']
        verbose_name = "Document Template"
        verbose_name_plural = "Document Templates"
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.name}"

class GeneratedDocument(models.Model):
    """Track all generated documents"""
    DOCUMENT_STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('VIEWED', 'Viewed'),
        ('SIGNED', 'Signed'),
        ('ARCHIVED', 'Archived'),
    ]
    
    document_number = models.CharField(max_length=100, unique=True, editable=False)
    document_type = models.CharField(max_length=50, choices=DocumentTemplate.DOCUMENT_TYPE_CHOICES)
    
    # Foreign keys to related documents/entities
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, null=True, blank=True)
    invoice = models.ForeignKey('finance.Invoice', on_delete=models.CASCADE, null=True, blank=True)
    lease_agreement = models.ForeignKey('hiring.LeaseAgreement', on_delete=models.CASCADE, null=True, blank=True)
    delivery_note = models.ForeignKey(DeliveryNote, on_delete=models.CASCADE, null=True, blank=True)
    goods_received_voucher = models.ForeignKey(GoodsReceivedVoucher, on_delete=models.CASCADE, null=True, blank=True)
    request_for_quotation = models.ForeignKey(RequestForQuotation, on_delete=models.CASCADE, null=True, blank=True)
    
    # Document metadata
    template = models.ForeignKey(DocumentTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    document_file = models.FileField(upload_to='generated_documents/', null=True, blank=True)
    file_name = models.CharField(max_length=500)
    file_size = models.IntegerField(default=0)
    file_type = models.CharField(max_length=50, default='pdf')
    
    # Status tracking
    status = models.CharField(max_length=50, choices=DOCUMENT_STATUS_CHOICES, default='DRAFT')
    generated_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='documents_generated')
    generated_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking information
    sent_to_email = models.EmailField(null=True, blank=True)
    view_count = models.IntegerField(default=0)
    download_count = models.IntegerField(default=0)
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    last_downloaded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-generated_at']
        verbose_name = "Generated Document"
        verbose_name_plural = "Generated Documents"
    
    def __str__(self):
        return f"{self.document_number} - {self.get_document_type_display()}"
    
    def save(self, *args, **kwargs):
        if not self.document_number:
            prefix = {
                'QUOTATION': 'QT',
                'INVOICE': 'INV',
                'LEASE_AGREEMENT': 'LA',
                'DELIVERY_NOTE': 'DN',
                'GOODS_RECEIVED_VOUCHER': 'GRV',
                'REQUEST_FOR_QUOTATION': 'RFQ',
                'RECEIPT': 'RCT'
            }.get(self.document_type, 'DOC')
            
            year = timezone.now().year
            month = timezone.now().month
            
            last_doc = GeneratedDocument.objects.filter(
                document_number__startswith=f'{prefix}-{year}-{month:02d}'
            ).order_by('document_number').last()
            
            if last_doc:
                last_number = int(last_doc.document_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.document_number = f'{prefix}-{year}-{month:02d}-{new_number:04d}'
        
        if self.document_file:
            self.file_size = self.document_file.size
        
        super().save(*args, **kwargs)
    
    def mark_as_sent(self, email=None):
        self.status = 'SENT'
        self.sent_at = timezone.now()
        if email:
            self.sent_to_email = email
        self.save()
    
    def mark_as_viewed(self):
        self.view_count += 1
        self.last_viewed_at = timezone.now()
        if self.status != 'VIEWED':
            self.status = 'VIEWED'
            self.viewed_at = timezone.now()
        self.save()
    
    def mark_as_signed(self):
        self.status = 'SIGNED'
        self.signed_at = timezone.now()
        self.save()
    
    def increment_download_count(self):
        self.download_count += 1
        self.last_downloaded_at = timezone.now()
        self.save()
    
    def get_related_object(self):
        """Get the related business object"""
        if self.quotation:
            return self.quotation
        elif self.invoice:
            return self.invoice
        elif self.lease_agreement:
            return self.lease_agreement
        elif self.delivery_note:
            return self.delivery_note
        elif self.goods_received_voucher:
            return self.goods_received_voucher
        elif self.request_for_quotation:
            return self.request_for_quotation
        return None
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('documents:document_detail', kwargs={'pk': self.pk})
    
    def get_download_url(self):
        from django.urls import reverse
        return reverse('documents:document_download', kwargs={'pk': self.pk})
    
    def get_preview_url(self):
        from django.urls import reverse
        return reverse('documents:document_preview', kwargs={'pk': self.pk})

class DocumentLog(models.Model):
    """Audit log for document activities"""
    ACTION_CHOICES = [
        ('GENERATED', 'Generated'),
        ('SENT', 'Sent'),
        ('VIEWED', 'Viewed'),
        ('DOWNLOADED', 'Downloaded'),
        ('SIGNED', 'Signed'),
        ('ARCHIVED', 'Archived'),
        ('DELETED', 'Deleted'),
        ('UPDATED', 'Updated'),
    ]
    
    document = models.ForeignKey(GeneratedDocument, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Document Log"
        verbose_name_plural = "Document Logs"
    
    def __str__(self):
        return f"{self.document.document_number} - {self.get_action_display()} at {self.created_at}"

class DocumentSetting(models.Model):
    """System-wide document settings"""
    company_name = models.CharField(max_length=200, default="Fossil Contracting")
    company_address = models.TextField(default="123 Industrial Area, Harare, Zimbabwe")
    company_phone = models.CharField(max_length=50, default="+263 242 123456")
    company_email = models.EmailField(default="info@fossilcontracting.co.zw")
    company_website = models.URLField(default="https://www.fossilcontracting.co.zw")
    company_logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    
    # Tax settings for Zimbabwe
    vat_number = models.CharField(max_length=50, default="VAT123456789")
    tin_number = models.CharField(max_length=50, default="TIN987654321")
    vat_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=15.00)
    
    # Document defaults
    quotation_validity_days = models.IntegerField(default=30)
    invoice_due_days = models.IntegerField(default=30)
    default_currency = models.CharField(max_length=10, default="USD")
    currency_symbol = models.CharField(max_length=5, default="$")
    
    # Footer information
    footer_text = models.TextField(default="Thank you for your business!")
    terms_and_conditions = models.TextField(default="Standard terms and conditions apply.")
    
    # Email settings
    send_document_emails = models.BooleanField(default=True)
    email_subject_prefix = models.CharField(max_length=100, default="[Fossil Contracting]")
    email_signature = models.TextField(default="Best regards,\nThe Fossil Contracting Team")
    
    # Archive settings
    auto_archive_days = models.IntegerField(default=730, help_text="Documents older than this will be archived (2 years)")
    auto_delete_days = models.IntegerField(default=1095, help_text="Documents older than this will be deleted (3 years)")
    
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Document Setting"
        verbose_name_plural = "Document Settings"
    
    def __str__(self):
        return "Document Settings"
    
    def save(self, *args, **kwargs):
        # Ensure only one settings instance exists
        if not self.pk and DocumentSetting.objects.exists():
            raise ValidationError('Only one DocumentSetting instance can exist')
        super().save(*args, **kwargs)

class DocumentCategory(models.Model):
    """Category for organizing documents"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff', help_text="Hex color code")
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome icon class")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Document Category"
        verbose_name_plural = "Document Categories"
    
    def __str__(self):
        return self.name

class ArchivedDocument(models.Model):
    """Store archived documents separately"""
    original_document = models.OneToOneField(GeneratedDocument, on_delete=models.CASCADE)
    archived_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    archived_at = models.DateTimeField(auto_now_add=True)
    archive_reason = models.TextField(blank=True)
    storage_location = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-archived_at']
        verbose_name = "Archived Document"
        verbose_name_plural = "Archived Documents"
    
    def __str__(self):
        return f"Archived: {self.original_document.document_number}"