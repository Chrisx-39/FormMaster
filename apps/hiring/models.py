from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from apps.accounts.models import User
from apps.clients.models import Client
from apps.inventory.models import Material
import uuid

class RequestForQuotation(models.Model):
    STATUS_CHOICES = [
        ('RECEIVED', 'Received'),
        ('QUOTED', 'Quoted'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('EXPIRED', 'Expired'),
    ]
    
    rfq_number = models.CharField(max_length=50, unique=True, editable=False)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    received_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='rfqs_received')
    received_date = models.DateTimeField(auto_now_add=True)
    required_date = models.DateField()
    hire_duration_days = models.IntegerField(validators=[MinValueValidator(1)])
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='RECEIVED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-received_date']
        verbose_name = "Request for Quotation"
        verbose_name_plural = "Requests for Quotation"
    
    def __str__(self):
        return f"RFQ-{self.rfq_number}"
    
    def save(self, *args, **kwargs):
        if not self.rfq_number:
            year = timezone.now().year
            last_rfq = RequestForQuotation.objects.filter(
                rfq_number__startswith=f'RFQ-{year}'
            ).order_by('rfq_number').last()
            
            if last_rfq:
                last_number = int(last_rfq.rfq_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.rfq_number = f'RFQ-{year}-{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def get_total_estimated_cost(self):
        """Calculate total estimated cost for this RFQ"""
        total = 0
        for item in self.items.all():
            daily_rate = item.material.daily_hire_rate if item.material.daily_hire_rate else 0
            total += daily_rate * item.quantity_requested * self.hire_duration_days
        return total

class RFQItem(models.Model):
    rfq = models.ForeignKey(RequestForQuotation, on_delete=models.CASCADE, related_name="items")
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    quantity_requested = models.IntegerField(validators=[MinValueValidator(1)])
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "RFQ Item"
        verbose_name_plural = "RFQ Items"
    
    def __str__(self):
        return f"{self.material.name} - {self.quantity_requested}"

class Quotation(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('EXPIRED', 'Expired'),
    ]
    
    quotation_number = models.CharField(max_length=50, unique=True, editable=False)
    rfq = models.ForeignKey(RequestForQuotation, on_delete=models.PROTECT, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    prepared_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="quotations_prepared")
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT, 
                                   related_name="quotations_approved", null=True, blank=True)
    date_prepared = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateField()
    hire_duration_days = models.IntegerField(validators=[MinValueValidator(1)])
    transport_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='DRAFT')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_prepared']
        verbose_name = "Quotation"
        verbose_name_plural = "Quotations"
    
    def __str__(self):
        return f"QT-{self.quotation_number}"
    
    def save(self, *args, **kwargs):
        if not self.quotation_number:
            year = timezone.now().year
            last_quote = Quotation.objects.filter(
                quotation_number__startswith=f'QT-{year}'
            ).order_by('quotation_number').last()
            
            if last_quote:
                last_number = int(last_quote.quotation_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.quotation_number = f'QT-{year}-{new_number:04d}'
        
        # Calculate totals before saving
        self.calculate_totals()
        super().save(*args, **kwargs)
    
    def calculate_totals(self):
        """Calculate subtotal, tax, and total amounts"""
        from django.conf import settings
        
        # Calculate subtotal from items
        subtotal = sum(item.line_total for item in self.items.all())
        subtotal += self.transport_cost
        
        # Calculate tax (15% VAT for Zimbabwe)
        tax_rate = getattr(settings, 'TAX_RATE', 0.15)  # Default to 15%
        tax_amount = subtotal * tax_rate
        
        # Calculate total
        total_amount = subtotal + tax_amount
        
        self.subtotal = subtotal
        self.tax_amount = tax_amount
        self.total_amount = total_amount
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('hiring:quotation_detail', kwargs={'pk': self.pk})

class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = "Quotation Item"
        verbose_name_plural = "Quotation Items"
    
    def __str__(self):
        return f"{self.material.name} - {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Calculate line total before saving
        self.line_total = self.daily_rate * self.quantity * self.duration_days
        super().save(*args, **kwargs)

class HireOrder(models.Model):
    STATUS_CHOICES = [
        ('ORDERED', 'Ordered'),
        ('APPROVED', 'Approved'),
        ('DISPATCHED', 'Dispatched'),
        ('ACTIVE', 'Active Rental'),
        ('RETURNED', 'Returned'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partial'),
        ('FULL', 'Full'),
        ('OVERDUE', 'Overdue'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True, editable=False)
    quotation = models.ForeignKey(Quotation, on_delete=models.PROTECT)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    order_date = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField()
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    hire_duration_days = models.IntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='ORDERED')
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-order_date']
        verbose_name = "Hire Order"
        verbose_name_plural = "Hire Orders"
    
    def __str__(self):
        return f"OR-{self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            year = timezone.now().year
            last_order = HireOrder.objects.filter(
                order_number__startswith=f'OR-{year}'
            ).order_by('order_number').last()
            
            if last_order:
                last_number = int(last_order.order_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.order_number = f'OR-{year}-{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('hiring:order_detail', kwargs={'pk': self.pk})
    
    def days_overdue(self):
        """Calculate number of days overdue"""
        if self.actual_return_date and self.actual_return_date > self.expected_return_date:
            return (self.actual_return_date - self.expected_return_date).days
        elif self.status == 'ACTIVE' and timezone.now().date() > self.expected_return_date:
            return (timezone.now().date() - self.expected_return_date).days
        return 0
    
    def calculate_late_penalty(self):
        """Calculate late return penalty"""
        from django.conf import settings
        days_overdue = self.days_overdue()
        if days_overdue > 0:
            penalty_rate = getattr(settings, 'LATE_RETURN_PENALTY_RATE', 50.00)
            return days_overdue * penalty_rate
        return 0
    
    def get_total_amount(self):
        """Get total amount from quotation"""
        return self.quotation.total_amount if self.quotation else 0
    
    def get_items_summary(self):
        """Get summary of items in this order"""
        return ", ".join([f"{item.material.name} ({item.quantity_ordered})" 
                         for item in self.items.all()])

class HireOrderItem(models.Model):
    CONDITION_CHOICES = [
        ('GOOD', 'Good'),
        ('FAIR', 'Fair'),
        ('DAMAGED', 'Damaged'),
        ('LOST', 'Lost'),
    ]
    
    hire_order = models.ForeignKey(HireOrder, on_delete=models.CASCADE, related_name='items')
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    quantity_ordered = models.IntegerField(validators=[MinValueValidator(1)])
    quantity_dispatched = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    quantity_returned = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    condition_on_return = models.CharField(max_length=50, choices=CONDITION_CHOICES, blank=True)
    
    class Meta:
        verbose_name = "Hire Order Item"
        verbose_name_plural = "Hire Order Items"
    
    def __str__(self):
        return f"{self.material.name} - Ordered: {self.quantity_ordered}"
    
    def get_pending_dispatch(self):
        """Get quantity pending dispatch"""
        return self.quantity_ordered - self.quantity_dispatched
    
    def get_pending_return(self):
        """Get quantity pending return"""
        return self.quantity_dispatched - self.quantity_returned
    
    def get_damaged_count(self):
        """Get damaged quantity if any"""
        if self.condition_on_return == 'DAMAGED':
            return self.quantity_returned
        return 0
    
    def is_fully_dispatched(self):
        """Check if item is fully dispatched"""
        return self.quantity_dispatched >= self.quantity_ordered
    
    def is_fully_returned(self):
        """Check if item is fully returned"""
        return self.quantity_returned >= self.quantity_dispatched

class LeaseAgreement(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('TERMINATED', 'Terminated'),
    ]
    
    agreement_number = models.CharField(max_length=50, unique=True, editable=False)
    hire_order = models.OneToOneField(HireOrder, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    hire_duration_days = models.IntegerField()
    late_return_penalty_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=50)
    damage_assessment_policy = models.TextField()
    signed_by_client = models.BooleanField(default=False)
    client_signature_date = models.DateField(null=True, blank=True)
    signed_by_fsm = models.ForeignKey(User, on_delete=models.PROTECT, 
                                     related_name="lease_agreements_signed", null=True, blank=True)
    fsm_signature_date = models.DateField(null=True, blank=True)
    agreement_document = models.FileField(upload_to="lease_agreements/", null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='DRAFT')
    terms_and_conditions = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Lease Agreement"
        verbose_name_plural = "Lease Agreements"
    
    def __str__(self):
        return f"LA-{self.agreement_number}"
    
    def save(self, *args, **kwargs):
        if not self.agreement_number:
            year = timezone.now().year
            last_agreement = LeaseAgreement.objects.filter(
                agreement_number__startswith=f'LA-{year}'
            ).order_by('agreement_number').last()
            
            if last_agreement:
                last_number = int(last_agreement.agreement_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.agreement_number = f'LA-{year}-{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('hiring:lease_detail', kwargs={'pk': self.pk})
    
    def is_fully_signed(self):
        """Check if lease agreement is fully signed"""
        return self.signed_by_client and self.signed_by_fsm is not None
    
    def get_total_amount(self):
        """Get total amount from hire order"""
        return self.hire_order.get_total_amount()
    
    def calculate_late_penalty(self, days_overdue):
        """Calculate late penalty based on days overdue"""
        return days_overdue * self.late_return_penalty_per_day