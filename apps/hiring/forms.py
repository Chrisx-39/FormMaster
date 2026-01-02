from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    RequestForQuotation, RFQItem, Quotation,
    QuotationItem, HireOrder, HireOrderItem, LeaseAgreement
)
from apps.inventory.models import Material
from apps.clients.models import Client

class RFQForm(forms.ModelForm):
    class Meta:
        model = RequestForQuotation
        fields = ['client', 'required_date', 'hire_duration_days', 'notes']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-control'}),
            'required_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().isoformat()
            }),
            'hire_duration_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter any special requirements or notes...'
            }),
        }
    
    def clean_required_date(self):
        required_date = self.cleaned_data['required_date']
        if required_date < timezone.now().date():
            raise ValidationError('Required date cannot be in the past.')
        return required_date
    
    def clean_hire_duration_days(self):
        duration = self.cleaned_data['hire_duration_days']
        if duration < 1:
            raise ValidationError('Hire duration must be at least 1 day.')
        if duration > 365:
            raise ValidationError('Hire duration cannot exceed 365 days.')
        return duration

class RFQItemForm(forms.ModelForm):
    material = forms.ModelChoiceField(
        queryset=Material.objects.filter(available_quantity__gt=0),
        widget=forms.Select(attrs={"class": "form-select"})
    )


    
    class Meta:
        model = RFQItem
        fields = ['material', 'quantity_requested', 'notes']
        widgets = {
            'quantity_requested': forms.NumberInput(attrs={
                'class': 'form-control quantity-input',
                'min': 1
            }),
            'notes': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional notes...'
            }),
        }
    
    def clean_quantity_requested(self):
        quantity = self.cleaned_data['quantity_requested']
        if quantity < 1:
            raise ValidationError('Quantity must be at least 1.')
        return quantity

RFQItemFormSet = inlineformset_factory(
    RequestForQuotation, RFQItem,
    form=RFQItemForm,
    extra=1,
    can_delete=True,
    can_delete_extra=True
)

class QuotationForm(forms.ModelForm):
    class Meta:
        model = Quotation
        fields = ['client', 'valid_until', 'transport_cost', 'notes']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-control'}),
            'valid_until': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().isoformat()
            }),
            'transport_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter any terms or conditions...'
            }),
        }
    
    def clean_valid_until(self):
        valid_until = self.cleaned_data['valid_until']
        if valid_until < timezone.now().date():
            raise ValidationError('Valid until date cannot be in the past.')
        return valid_until

class QuotationItemForm(forms.ModelForm):
    material = forms.ModelChoiceField(
        queryset=Material.objects.filter(available_quantity__gt=0),
        widget=forms.Select(attrs={"class": "form-select"})
    )

    
    class Meta:
        model = QuotationItem
        fields = ['material', 'quantity', 'daily_rate', 'duration_days']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control quantity-input',
                'min': 1
            }),
            'daily_rate': forms.NumberInput(attrs={
                'class': 'form-control rate-input',
                'step': '0.01',
                'min': '0.01'
            }),
            'duration_days': forms.NumberInput(attrs={
                'class': 'form-control duration-input',
                'min': 1
            }),
        }
    
    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity < 1:
            raise ValidationError('Quantity must be at least 1.')
        return quantity
    
    def clean_daily_rate(self):
        rate = self.cleaned_data['daily_rate']
        if rate <= 0:
            raise ValidationError('Daily rate must be greater than 0.')
        return rate
    
    def clean_duration_days(self):
        duration = self.cleaned_data['duration_days']
        if duration < 1:
            raise ValidationError('Duration must be at least 1 day.')
        return duration

QuotationItemFormSet = inlineformset_factory(
    Quotation, QuotationItem,
    form=QuotationItemForm,
    extra=1,
    can_delete=True
)

class HireOrderForm(forms.ModelForm):
    class Meta:
        model = HireOrder
        fields = ['start_date', 'expected_return_date']
        widgets = {
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().isoformat()
            }),
            'expected_return_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().isoformat()
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        expected_return_date = cleaned_data.get('expected_return_date')
        
        if start_date and expected_return_date:
            if start_date >= expected_return_date:
                raise ValidationError('Start date must be before expected return date.')
            
            # Ensure hire duration is reasonable
            duration = (expected_return_date - start_date).days
            if duration > 365:
                raise ValidationError('Hire duration cannot exceed 365 days.')
        
        return cleaned_data

class HireOrderItemForm(forms.ModelForm):
    class Meta:
        model = HireOrderItem
        fields = ['material', 'quantity_ordered']
        widgets = {
            'material': forms.Select(attrs={'class': 'form-control'}),
            'quantity_ordered': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
        }

HireOrderItemFormSet = inlineformset_factory(
    HireOrder, HireOrderItem,
    form=HireOrderItemForm,
    extra=0,
    can_delete=True
)

class LeaseAgreementForm(forms.ModelForm):
    class Meta:
        model = LeaseAgreement
        fields = ['late_return_penalty_per_day', 'damage_assessment_policy', 'terms_and_conditions']
        widgets = {
            'late_return_penalty_per_day': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'damage_assessment_policy': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'terms_and_conditions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10
            }),
        }
    
    def clean_late_return_penalty_per_day(self):
        penalty = self.cleaned_data['late_return_penalty_per_day']
        if penalty <= 0:
            raise ValidationError('Late return penalty must be greater than 0.')
        return penalty