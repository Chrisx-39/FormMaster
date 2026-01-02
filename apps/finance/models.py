from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from apps.accounts.models import User
from apps.hiring.models import Client, HireOrder

class Invoice(models.Model):
    INVOICE_TYPE_CHOICES = [
        ('ADVANCE', 'Advance Payment'),
        ('FINAL', 'Final Payment'),
        ('PENALTY', 'Penalty/Damage'),
        ('PARTIAL', 'Partial Payment'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ISSUED', 'Issued'),
        ('SENT', 'Sent'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    hire_order = models.ForeignKey(HireOrder, on_delete=models.PROTECT)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    invoice_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='DRAFT')
    invoice_type = models.CharField(max_length=50, choices=INVOICE_TYPE_CHOICES)
    notes = models.TextField(blank=True)
    issued_by = models.ForeignKey(User, on_delete=models.PROTECT)
    document = models.FileField(upload_to='invoices/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
    
    def __str__(self):
        return f"INV-{self.invoice_number}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            year = timezone.now().year
            last_invoice = Invoice.objects.filter(
                invoice_number__startswith=f'INV-{year}'
            ).order_by('invoice_number').last()
            
            if last_invoice:
                last_number = int(last_invoice.invoice_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.invoice_number = f'INV-{year}-{new_number:04d}'
        
        # Calculate balance due
        self.balance_due = self.total_amount - self.amount_paid
        
        # Update payment status
        if self.amount_paid >= self.total_amount:
            self.payment_status = 'PAID'
        elif self.amount_paid > 0:
            self.payment_status = 'PARTIAL'
        elif self.due_date < timezone.now().date() and self.payment_status == 'SENT':
            self.payment_status = 'OVERDUE'
        
        super().save(*args, **kwargs)
    
    def calculate_totals(self, subtotal):
        from django.conf import settings
        self.subtotal = subtotal
        self.tax_amount = subtotal * settings.TAX_RATE
        self.total_amount = self.subtotal + self.tax_amount
        self.balance_due = self.total_amount - self.amount_paid
    
    def is_overdue(self):
        return self.due_date < timezone.now().date() and self.payment_status != 'PAID'
    
    def days_overdue(self):
        if self.is_overdue():
            return (timezone.now().date() - self.due_date).days
        return 0

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
        ('CREDIT_CARD', 'Credit Card'),
        ('MOBILE_MONEY', 'Mobile Money'),
    ]
    
    payment_number = models.CharField(max_length=50, unique=True, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    payment_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100)
    received_by = models.ForeignKey(User, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    confirmed = models.BooleanField(default=False)
    confirmed_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='payments_confirmed', null=True, blank=True)
    confirmation_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
    
    def __str__(self):
        return f"PAY-{self.payment_number}"
    
    def save(self, *args, **kwargs):
        if not self.payment_number:
            year = timezone.now().year
            last_payment = Payment.objects.filter(
                payment_number__startswith=f'PAY-{year}'
            ).order_by('payment_number').last()
            
            if last_payment:
                last_number = int(last_payment.payment_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.payment_number = f'PAY-{year}-{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def confirm_payment(self, user):
        self.confirmed = True
        self.confirmed_by = user
        self.confirmation_date = timezone.now()
        self.save()
        
        # Update invoice amount paid
        invoice = self.invoice
        total_paid = sum(p.amount for p in invoice.payments.filter(confirmed=True))
        invoice.amount_paid = total_paid
        
        if total_paid >= invoice.total_amount:
            invoice.payment_status = 'PAID'
        elif total_paid > 0:
            invoice.payment_status = 'PARTIAL'
        
        invoice.save()

class RevenueRecord(models.Model):
    hire_order = models.ForeignKey(HireOrder, on_delete=models.PROTECT)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    period_start = models.DateField()
    period_end = models.DateField()
    base_hire_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transport_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    penalty_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    damage_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    recorded_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Revenue Record"
        verbose_name_plural = "Revenue Records"
        unique_together = ['hire_order', 'period_start', 'period_end']
    
    def __str__(self):
        return f"Revenue for OR-{self.hire_order.order_number} ({self.period_start} to {self.period_end})"
    
    def save(self, *args, **kwargs):
        self.total_revenue = (self.base_hire_revenue + 
                             self.transport_revenue + 
                             self.penalty_revenue + 
                             self.damage_revenue)
        super().save(*args, **kwargs)

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('FUEL', 'Fuel'),
        ('MAINTENANCE', 'Vehicle Maintenance'),
        ('REPAIRS', 'Equipment Repairs'),
        ('SALARIES', 'Salaries'),
        ('UTILITIES', 'Utilities'),
        ('OFFICE_SUPPLIES', 'Office Supplies'),
        ('INSURANCE', 'Insurance'),
        ('OTHER', 'Other'),
    ]
    
    expense_number = models.CharField(max_length=50, unique=True, editable=False)
    date = models.DateField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    vendor = models.CharField(max_length=200, blank=True)
    invoice_reference = models.CharField(max_length=100, blank=True)
    paid_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    payment_method = models.CharField(max_length=50, choices=Payment.PAYMENT_METHOD_CHOICES, default='CASH')
    receipt = models.FileField(upload_to='expenses/', null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='expenses_approved', null=True, blank=True)
    approved_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
    
    def __str__(self):
        return f"EXP-{self.expense_number}"
    
    def save(self, *args, **kwargs):
        if not self.expense_number:
            year = timezone.now().year
            last_expense = Expense.objects.filter(
                expense_number__startswith=f'EXP-{year}'
            ).order_by('expense_number').last()
            
            if last_expense:
                last_number = int(last_expense.expense_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.expense_number = f'EXP-{year}-{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def approve(self, user):
        self.approved_by = user
        self.approved_date = timezone.now().date()
        self.save()