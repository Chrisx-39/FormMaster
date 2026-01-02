from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from apps.accounts.models import User
from apps.hiring.models import HireOrder

class TransportRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('ASSIGNED', 'Assigned'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    TRUCK_TYPE_CHOICES = [
        ('SMALL', 'Small Truck (5-10 tons)'),
        ('MEDIUM', 'Medium Truck (10-20 tons)'),
        ('LARGE', 'Large Truck (20-30 tons)'),
        ('FLATBED', 'Flatbed Truck'),
        ('CRANE', 'Crane Truck'),
    ]
    
    request_number = models.CharField(max_length=50, unique=True, editable=False)
    hire_order = models.ForeignKey(HireOrder, on_delete=models.CASCADE)
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="transport_requests")
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="transport_approvals", null=True, blank=True)
    request_date = models.DateTimeField(auto_now_add=True)
    required_date = models.DateField()
    truck_type_required = models.CharField(max_length=100, choices=TRUCK_TYPE_CHOICES)
    delivery_address = models.TextField()
    special_instructions = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Transport Request"
        verbose_name_plural = "Transport Requests"
        ordering = ['-request_date']
    
    def __str__(self):
        return f"TR-{self.request_number}"
    
    def save(self, *args, **kwargs):
        if not self.request_number:
            year = timezone.now().year
            last_request = TransportRequest.objects.filter(
                request_number__startswith=f'TR-{year}'
            ).order_by('request_number').last()
            
            if last_request:
                last_number = int(last_request.request_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.request_number = f'TR-{year}-{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('delivery:transport_detail', kwargs={'pk': self.pk})

class Delivery(models.Model):
    DELIVERY_TYPE_CHOICES = [
        ('OUTGOING', 'Outgoing'),
        ('RETURN', 'Return'),
    ]
    
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_TRANSIT', 'In Transit'),
        ('DELIVERED', 'Delivered'),
        ('RETURNED', 'Returned'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    delivery_number = models.CharField(max_length=50, unique=True, editable=False)
    hire_order = models.ForeignKey(HireOrder, on_delete=models.CASCADE)
    transport_request = models.ForeignKey(TransportRequest, on_delete=models.PROTECT, null=True, blank=True)
    driver_name = models.CharField(max_length=200)
    driver_phone = models.CharField(max_length=20)
    truck_registration = models.CharField(max_length=50)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField(null=True, blank=True)
    delivery_address = models.TextField()
    delivery_type = models.CharField(max_length=50, choices=DELIVERY_TYPE_CHOICES)
    inspected_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="deliveries_inspected", null=True, blank=True)
    inspection_notes = models.TextField(blank=True)
    is_safe_for_transport = models.BooleanField(default=False)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='SCHEDULED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Delivery"
        verbose_name_plural = "Deliveries"
        ordering = ['-departure_time']
    
    def __str__(self):
        return f"DEL-{self.delivery_number}"
    
    def save(self, *args, **kwargs):
        if not self.delivery_number:
            year = timezone.now().year
            last_delivery = Delivery.objects.filter(
                delivery_number__startswith=f'DEL-{year}'
            ).order_by('delivery_number').last()
            
            if last_delivery:
                last_number = int(last_delivery.delivery_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.delivery_number = f'DEL-{year}-{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('delivery:delivery_detail', kwargs={'pk': self.pk})
    
    def mark_as_delivered(self):
        self.status = 'DELIVERED'
        self.arrival_time = timezone.now()
        self.save()

class DeliveryNote(models.Model):
    note_number = models.CharField(max_length=50, unique=True, editable=False)
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE)
    issued_date = models.DateTimeField(auto_now_add=True)
    signed_by_driver = models.BooleanField(default=False)
    signed_by_scaffolder = models.BooleanField(default=False)
    signed_by_security = models.BooleanField(default=False)
    signed_by_client = models.BooleanField(default=False)
    driver_signature_date = models.DateTimeField(null=True, blank=True)
    scaffolder_signature_date = models.DateTimeField(null=True, blank=True)
    security_signature_date = models.DateTimeField(null=True, blank=True)
    client_signature_date = models.DateTimeField(null=True, blank=True)
    document = models.FileField(upload_to="delivery_notes/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Delivery Note"
        verbose_name_plural = "Delivery Notes"
        ordering = ['-issued_date']
    
    def __str__(self):
        return f"DN-{self.note_number}"
    
    def save(self, *args, **kwargs):
        if not self.note_number:
            year = timezone.now().year
            last_note = DeliveryNote.objects.filter(
                note_number__startswith=f'DN-{year}'
            ).order_by('note_number').last()
            
            if last_note:
                last_number = int(last_note.note_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.note_number = f'DN-{year}-{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('delivery:delivery_note_detail', kwargs={'pk': self.pk})
    
    def is_fully_signed(self):
        return (self.signed_by_driver and 
                self.signed_by_scaffolder and 
                self.signed_by_security)

class DeliveryNoteItem(models.Model):
    CONDITION_CHOICES = [
        ('GOOD', 'Good'),
        ('FAIR', 'Fair'),
        ('POOR', 'Poor'),
        ('DAMAGED', 'Damaged'),
    ]
    
    delivery_note = models.ForeignKey(DeliveryNote, on_delete=models.CASCADE, related_name="items")
    material = models.ForeignKey('inventory.Material', on_delete=models.PROTECT)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    condition = models.CharField(max_length=50, choices=CONDITION_CHOICES, default='GOOD')
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Delivery Note Item"
        verbose_name_plural = "Delivery Note Items"
    
    def __str__(self):
        return f"{self.material.name} - {self.quantity}"

class GoodsReceivedVoucher(models.Model):
    grv_number = models.CharField(max_length=50, unique=True, editable=False)
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE)
    hire_order = models.ForeignKey(HireOrder, on_delete=models.CASCADE)
    received_date = models.DateTimeField(auto_now_add=True)
    received_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="grvs_received")
    issued_by_client = models.BooleanField(default=False)
    all_items_received = models.BooleanField(default=False)
    discrepancy_notes = models.TextField(blank=True)
    document = models.FileField(upload_to="grv_documents/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Goods Received Voucher"
        verbose_name_plural = "Goods Received Vouchers"
        ordering = ['-received_date']
    
    def __str__(self):
        return f"GRV-{self.grv_number}"
    
    def save(self, *args, **kwargs):
        if not self.grv_number:
            year = timezone.now().year
            last_grv = GoodsReceivedVoucher.objects.filter(
                grv_number__startswith=f'GRV-{year}'
            ).order_by('grv_number').last()
            
            if last_grv:
                last_number = int(last_grv.grv_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.grv_number = f'GRV-{year}-{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('delivery:grv_detail', kwargs={'pk': self.pk})

class GRVItem(models.Model):
    grv = models.ForeignKey(GoodsReceivedVoucher, on_delete=models.CASCADE, related_name="items")
    material = models.ForeignKey('inventory.Material', on_delete=models.PROTECT)
    quantity_expected = models.IntegerField(validators=[MinValueValidator(1)])
    quantity_received = models.IntegerField(validators=[MinValueValidator(0)])
    condition_on_receipt = models.CharField(max_length=50, choices=DeliveryNoteItem.CONDITION_CHOICES)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "GRV Item"
        verbose_name_plural = "GRV Items"
    
    def __str__(self):
        return f"{self.material.name} - Expected: {self.quantity_expected}, Received: {self.quantity_received}"
    
    def get_discrepancy(self):
        return self.quantity_expected - self.quantity_received
    
    def has_discrepancy(self):
        return self.quantity_expected != self.quantity_received