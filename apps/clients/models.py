from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, EmailValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField
from apps.accounts.models import User

class Client(models.Model):
    """Client model for both internal and external clients"""
    CLIENT_TYPE_CHOICES = [
        ('INTERNAL', 'Internal'),
        ('EXTERNAL', 'External'),
        ('GOVERNMENT', 'Government'),
        ('PRIVATE', 'Private'),
        ('INDIVIDUAL', 'Individual'),
    ]
    
    CLIENT_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('SUSPENDED', 'Suspended'),
        ('BLACKLISTED', 'Blacklisted'),
    ]
    
    PAYMENT_TERMS_CHOICES = [
        ('IMMEDIATE', 'Immediate Payment'),
        ('7_DAYS', '7 Days'),
        ('14_DAYS', '14 Days'),
        ('30_DAYS', '30 Days'),
        ('60_DAYS', '60 Days'),
        ('90_DAYS', '90 Days'),
    ]
    
    # Basic Information
    client_number = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=200)
    trading_as = models.CharField(max_length=200, blank=True, help_text="Trading name if different")
    client_type = models.CharField(max_length=20, choices=CLIENT_TYPE_CHOICES, default='EXTERNAL')
    status = models.CharField(max_length=20, choices=CLIENT_STATUS_CHOICES, default='ACTIVE')
    
    # Contact Information
    contact_person = models.CharField(max_length=200)
    position = models.CharField(max_length=100, blank=True)
    email = models.EmailField(validators=[EmailValidator()])
    phone = PhoneNumberField(region='ZW', help_text="Zimbabwe phone number format: +263 xxx xxx xxx")
    alternate_phone = PhoneNumberField(region='ZW', blank=True, null=True)
    fax = models.CharField(max_length=50, blank=True)
    
    # Address Information
    physical_address = models.TextField()
    postal_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, default='Harare')
    province = models.CharField(max_length=100, default='Harare')
    country = CountryField(default='ZW')
    gps_coordinates = models.CharField(max_length=100, blank=True, help_text="GPS coordinates (optional)")
    
    # Business Information
    registration_number = models.CharField(max_length=100, blank=True, help_text="Company registration number")
    tax_number = models.CharField(max_length=100, blank=True, help_text="Tax Identification Number (TIN)")
    vat_number = models.CharField(max_length=100, blank=True, help_text="VAT Registration Number")
    business_sector = models.CharField(max_length=200, blank=True)
    year_established = models.IntegerField(
    blank=True,
    null=True,
    validators=[MinValueValidator(1900)]  # keep only the static min validator
)
    
    # Financial Information
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    credit_rating = models.CharField(max_length=50, blank=True)
    payment_terms = models.CharField(max_length=20, choices=PAYMENT_TERMS_CHOICES, default='30_DAYS')
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, 
                                       validators=[MinValueValidator(0), MaxValueValidator(100)],
                                       help_text="Discount percentage (0-100)")
    
    # Relationship Management
    account_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                       related_name='managed_clients', limit_choices_to={'role__in': ['FSM', 'HCE']})
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='referrals')
    relationship_start_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    
    # Document References
    client_contract = models.FileField(upload_to='client_contracts/', blank=True, null=True)
    kyc_document = models.FileField(upload_to='client_kyc/', blank=True, null=True, 
                                   help_text="Know Your Customer document")
    certificate_of_registration = models.FileField(upload_to='client_registrations/', blank=True, null=True)
    
    # System Fields
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='clients_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        indexes = [
            models.Index(fields=['client_number']),
            models.Index(fields=['name']),
            models.Index(fields=['client_type']),
            models.Index(fields=['status']),
            models.Index(fields=['city']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.client_number})"
    
    def save(self, *args, **kwargs):
        if not self.client_number:
            # Generate client number: CL-YYYY-XXXX
            year = timezone.now().year
            last_client = Client.objects.filter(
                client_number__startswith=f'CL-{year}'
            ).order_by('client_number').last()
            
            if last_client:
                last_number = int(last_client.client_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.client_number = f'CL-{year}-{new_number:04d}'
        
        # Set postal address to physical address if not provided
        if not self.postal_address:
            self.postal_address = self.physical_address
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('clients:client_detail', kwargs={'pk': self.pk})
    
    def clean(self):
        """Validate client data"""
        super().clean()
        
        # Validate credit limit
        if self.credit_limit < 0:
            raise ValidationError({'credit_limit': 'Credit limit cannot be negative.'})
        
        # Validate discount rate
        if self.discount_rate < 0 or self.discount_rate > 100:
            raise ValidationError({'discount_rate': 'Discount rate must be between 0 and 100.'})
        
        # Validate year established
        if self.year_established and self.year_established > timezone.now().year:
            raise ValidationError({'year_established': 'Year established cannot be in the future.'})
    
    @property
    def available_credit(self):
        """Calculate available credit"""
        return max(self.credit_limit - self.current_balance, 0)
    
    @property
    def credit_utilization(self):
        """Calculate credit utilization percentage"""
        if self.credit_limit > 0:
            return (self.current_balance / self.credit_limit) * 100
        return 0
    
    @property
    def is_credit_available(self):
        """Check if credit is available"""
        return self.available_credit > 0
    
    @property
    def credit_status(self):
        """Get credit status based on utilization"""
        utilization = self.credit_utilization
        
        if utilization >= 90:
            return 'CRITICAL'
        elif utilization >= 75:
            return 'HIGH'
        elif utilization >= 50:
            return 'MODERATE'
        else:
            return 'LOW'
    
    @property
    def full_address(self):
        """Get formatted full address"""
        parts = [self.physical_address]
        if self.city:
            parts.append(self.city)
        if self.province:
            parts.append(self.province)
        if self.country:
            parts.append(str(self.country))
        return ', '.join(parts)
    
    def update_balance(self, amount):
        """Update client balance"""
        self.current_balance += amount
        self.save()
    
    def mark_as_verified(self):
        """Mark client as verified"""
        self.is_verified = True
        self.verification_date = timezone.now().date()
        self.save()
    
    def get_payment_terms_days(self):
        """Get payment terms in days"""
        terms_map = {
            'IMMEDIATE': 0,
            '7_DAYS': 7,
            '14_DAYS': 14,
            '30_DAYS': 30,
            '60_DAYS': 60,
            '90_DAYS': 90,
        }
        return terms_map.get(self.payment_terms, 30)

class ClientContact(models.Model):
    """Additional contacts for a client"""
    CONTACT_TYPE_CHOICES = [
        ('PRIMARY', 'Primary Contact'),
        ('SECONDARY', 'Secondary Contact'),
        ('ACCOUNTS', 'Accounts Department'),
        ('TECHNICAL', 'Technical Contact'),
        ('PROCUREMENT', 'Procurement'),
        ('SITE_MANAGER', 'Site Manager'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=200)
    position = models.CharField(max_length=100)
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPE_CHOICES, default='SECONDARY')
    email = models.EmailField(blank=True)
    phone = PhoneNumberField(region='ZW', blank=True)
    mobile = PhoneNumberField(region='ZW', blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['client', 'contact_type', 'name']
        verbose_name = "Client Contact"
        verbose_name_plural = "Client Contacts"
        unique_together = ['client', 'email']
    
    def __str__(self):
        return f"{self.name} - {self.get_contact_type_display()} ({self.client.name})"

class ClientSite(models.Model):
    """Client site/location information"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='sites')
    site_name = models.CharField(max_length=200)
    site_code = models.CharField(max_length=50, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    gps_coordinates = models.CharField(max_length=100, blank=True)
    site_manager = models.CharField(max_length=200, blank=True)
    site_phone = PhoneNumberField(region='ZW', blank=True)
    is_active = models.BooleanField(default=True)
    is_main_site = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['client', 'site_name']
        verbose_name = "Client Site"
        verbose_name_plural = "Client Sites"
        unique_together = ['client', 'site_name']
    
    def __str__(self):
        return f"{self.site_name} ({self.client.name})"
    
    def save(self, *args, **kwargs):
        # Ensure only one main site per client
        if self.is_main_site:
            ClientSite.objects.filter(client=self.client, is_main_site=True).update(is_main_site=False)
        super().save(*args, **kwargs)

class ClientDocument(models.Model):
    """Documents related to clients"""
    DOCUMENT_TYPE_CHOICES = [
        ('CONTRACT', 'Contract'),
        ('KYC', 'KYC Document'),
        ('CERTIFICATE', 'Certificate of Registration'),
        ('TAX_CLEARANCE', 'Tax Clearance Certificate'),
        ('BANK_DETAILS', 'Bank Details'),
        ('ID', 'ID Document'),
        ('INSURANCE', 'Insurance Certificate'),
        ('OTHER', 'Other'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    document_file = models.FileField(upload_to='client_documents/')
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Client Document"
        verbose_name_plural = "Client Documents"
    
    def __str__(self):
        return f"{self.name} - {self.client.name}"
    
    @property
    def is_expired(self):
        """Check if document is expired"""
        if self.valid_until:
            return self.valid_until < timezone.now().date()
        return False

class ClientNote(models.Model):
    """Notes and communications with clients"""
    NOTE_TYPE_CHOICES = [
        ('GENERAL', 'General Note'),
        ('MEETING', 'Meeting Notes'),
        ('PHONE_CALL', 'Phone Call'),
        ('EMAIL', 'Email'),
        ('VISIT', 'Site Visit'),
        ('COMPLAINT', 'Complaint'),
        ('FOLLOW_UP', 'Follow Up'),
        ('CREDIT_REVIEW', 'Credit Review'),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    client = models.ForeignKey(
    Client,
    on_delete=models.CASCADE,
    related_name='client_notes'
)

    note_type = models.CharField(max_length=50, choices=NOTE_TYPE_CHOICES, default='GENERAL')
    subject = models.CharField(max_length=200)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='client_notes')
    created_at = models.DateTimeField(auto_now_add=True)
    follow_up_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='resolved_notes')
    resolution_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Client Note"
        verbose_name_plural = "Client Notes"
    
    def __str__(self):
        return f"{self.subject} - {self.client.name}"
    
    def mark_as_resolved(self, user, notes=''):
        """Mark note as resolved"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.resolution_notes = notes
        self.save()

class ClientHistory(models.Model):
    """Audit trail for client changes"""
    ACTION_CHOICES = [
        ('CREATED', 'Created'),
        ('UPDATED', 'Updated'),
        ('STATUS_CHANGE', 'Status Changed'),
        ('CREDIT_LIMIT_CHANGE', 'Credit Limit Changed'),
        ('BALANCE_UPDATE', 'Balance Updated'),
        ('DOCUMENT_UPLOADED', 'Document Uploaded'),
        ('NOTE_ADDED', 'Note Added'),
        ('CONTACT_ADDED', 'Contact Added'),
        ('SITE_ADDED', 'Site Added'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.PROTECT)
    performed_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-performed_at']
        verbose_name = "Client History"
        verbose_name_plural = "Client History"
    
    def __str__(self):
        return f"{self.client.name} - {self.get_action_display()} at {self.performed_at}"

class CreditNote(models.Model):
    """Credit notes issued to clients"""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ISSUED', 'Issued'),
        ('APPLIED', 'Applied'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    credit_note_number = models.CharField(max_length=50, unique=True, editable=False)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='credit_notes')
    invoice = models.ForeignKey('finance.Invoice', on_delete=models.SET_NULL, null=True, blank=True, 
                               related_name='credit_notes')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    issued_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='issued_credit_notes')
    issued_date = models.DateField(default=timezone.now)
    valid_until = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    applied_to_invoice = models.ForeignKey('finance.Invoice', on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='applied_credit_notes')
    applied_date = models.DateField(null=True, blank=True)
    applied_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='applied_credit_notes')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-issued_date']
        verbose_name = "Credit Note"
        verbose_name_plural = "Credit Notes"
    
    def __str__(self):
        return f"CN-{self.credit_note_number} - {self.client.name}"
    
    def save(self, *args, **kwargs):
        if not self.credit_note_number:
            year = timezone.now().year
            last_note = CreditNote.objects.filter(
                credit_note_number__startswith=f'CN-{year}'
            ).order_by('credit_note_number').last()
            
            if last_note:
                last_number = int(last_note.credit_note_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.credit_note_number = f'CN-{year}-{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def apply_to_invoice(self, invoice, user):
        """Apply credit note to an invoice"""
        self.status = 'APPLIED'
        self.applied_to_invoice = invoice
        self.applied_date = timezone.now().date()
        self.applied_by = user
        self.save()
        
        # Update client balance
        self.client.update_balance(-self.amount)

class ClientRating(models.Model):
    """Client performance rating"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='ratings')
    rating_date = models.DateField(default=timezone.now)
    
    # Rating criteria (1-5 scale)
    payment_timeliness = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1=Very Poor, 5=Excellent"
    )
    communication = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    cooperation = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    volume_of_business = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    profitability = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    overall_score = models.DecimalField(max_digits=3, decimal_places=1, editable=False)
    comments = models.TextField(blank=True)
    rated_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-rating_date']
        verbose_name = "Client Rating"
        verbose_name_plural = "Client Ratings"
        unique_together = ['client', 'rating_date']
    
    def __str__(self):
        return f"Rating for {self.client.name} - {self.rating_date}"
    
    def save(self, *args, **kwargs):
        # Calculate overall score
        scores = [
            self.payment_timeliness,
            self.communication,
            self.cooperation,
            self.volume_of_business,
            self.profitability
        ]
        self.overall_score = sum(scores) / len(scores)
        super().save(*args, **kwargs)
    
    @property
    def rating_category(self):
        """Get rating category based on overall score"""
        if self.overall_score >= 4.5:
            return 'EXCELLENT'
        elif self.overall_score >= 4.0:
            return 'GOOD'
        elif self.overall_score >= 3.0:
            return 'SATISFACTORY'
        elif self.overall_score >= 2.0:
            return 'NEEDS_IMPROVEMENT'
        else:
            return 'POOR'

class BlacklistReason(models.Model):
    """Reasons for blacklisting clients"""
    reason_code = models.CharField(max_length=20, unique=True)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=[
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ])
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['severity', 'reason_code']
        verbose_name = "Blacklist Reason"
        verbose_name_plural = "Blacklist Reasons"
    
    def __str__(self):
        return f"{self.reason_code} - {self.description[:50]}"

class ClientBlacklist(models.Model):
    """Blacklisted clients"""
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='blacklist_entry')
    reason = models.ForeignKey(BlacklistReason, on_delete=models.PROTECT)
    blacklisted_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='blacklisted_clients')
    blacklisted_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    evidence_document = models.FileField(upload_to='blacklist_evidence/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-blacklisted_at']
        verbose_name = "Client Blacklist"
        verbose_name_plural = "Client Blacklist"
    
    def __str__(self):
        return f"Blacklisted: {self.client.name}"
    
    def save(self, *args, **kwargs):
        # Update client status when blacklisted
        if self.is_active:
            self.client.status = 'BLACKLISTED'
            self.client.save()
        super().save(*args, **kwargs)