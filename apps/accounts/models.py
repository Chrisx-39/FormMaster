# apps/accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinLengthValidator

class User(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('FSM', 'Formwork & Scaffolding Manager'),
        ('HCE', 'Hiring Cost Estimator'),
        ('ENGINEER', 'Engineer'),
        ('SCAFFOLDER', 'Scaffolder'),
        ('DRIVER', 'Driver'),
        ('SECURITY', 'Security Guard'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
    
    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"
    
    def is_admin(self):
        return self.role == 'ADMIN'
    
    def is_fsm(self):
        return self.role == 'FSM'
    
    def is_hce(self):
        return self.role == 'HCE'
    
    def is_scaffolder(self):
        return self.role == 'SCAFFOLDER'
    
    def can_approve_quotes(self):
        return self.role in ['FSM', 'ADMIN']
    
    def can_sign_leases(self):
        return self.role in ['FSM', 'ADMIN']
    
    def can_create_invoices(self):
        return self.role in ['HCE', 'FSM', 'ADMIN']