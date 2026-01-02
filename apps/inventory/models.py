from django.db import models
from django.core.validators import MinValueValidator
from apps.accounts.models import User

class MaterialCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    code = models.CharField(max_length=20, unique=True)
    
    class Meta:
        verbose_name = "Material Category"
        verbose_name_plural = "Material Categories"
    
    def __str__(self):
        return self.name

class Material(models.Model):
    CONDITION_CHOICES = [
        ('GOOD', 'Good'),
        ('FAIR', 'Fair'),
        ('DAMAGED', 'Damaged'),
        ('UNDER_MAINTENANCE', 'Under Maintenance'),
    ]
    
    category = models.ForeignKey(MaterialCategory, on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    unit_of_measure = models.CharField(max_length=50)
    daily_hire_rate = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    replacement_cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    condition = models.CharField(max_length=50, choices=CONDITION_CHOICES, default='GOOD')
    total_quantity = models.IntegerField(validators=[MinValueValidator(0)])
    available_quantity = models.IntegerField(validators=[MinValueValidator(0)])
    hired_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    minimum_stock_level = models.IntegerField(validators=[MinValueValidator(0)])
    location = models.CharField(max_length=200)
    last_inspection_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materials"
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def is_low_stock(self):
        return self.available_quantity <= self.minimum_stock_level
    
    def utilization_rate(self):
        if self.total_quantity > 0:
            return (self.hired_quantity / self.total_quantity) * 100
        return 0
    
    def save(self, *args, **kwargs):
        # Ensure available_quantity is not greater than total_quantity
        if self.available_quantity > self.total_quantity:
            self.available_quantity = self.total_quantity
        super().save(*args, **kwargs)

class MaterialInspection(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    inspector = models.ForeignKey(User, on_delete=models.PROTECT)
    inspection_date = models.DateTimeField(auto_now_add=True)
    condition = models.CharField(max_length=50, choices=Material.CONDITION_CHOICES)
    notes = models.TextField()
    is_safe_for_use = models.BooleanField()
    next_inspection_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Material Inspection"
        verbose_name_plural = "Material Inspections"
    
    def __str__(self):
        return f"Inspection of {self.material.code} on {self.inspection_date}"