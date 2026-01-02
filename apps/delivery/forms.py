from django import forms
from django.utils import timezone
from .models import *
from apps.hiring.models import HireOrder

class TransportRequestForm(forms.ModelForm):
    class Meta:
        model = TransportRequest
        fields = ['hire_order', 'required_date', 'truck_type_required', 
                 'delivery_address', 'special_instructions']
        widgets = {
            'required_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'delivery_address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'special_instructions': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'truck_type_required': forms.Select(attrs={'class': 'form-control'}),
            'hire_order': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hire_order'].queryset = HireOrder.objects.filter(status='APPROVED')

class TransportRequestApproveForm(forms.ModelForm):
    class Meta:
        model = TransportRequest
        fields = ['truck_type_required', 'delivery_address', 'special_instructions', 'status']
        widgets = {
            'delivery_address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'readonly': 'readonly'}),
            'special_instructions': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'readonly': 'readonly'}),
            'truck_type_required': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.HiddenInput(),
        }

class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ['hire_order', 'transport_request', 'driver_name', 'driver_phone',
                 'truck_registration', 'departure_time', 'delivery_address',
                 'delivery_type', 'inspection_notes', 'is_safe_for_transport']
        widgets = {
            'departure_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'delivery_address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'driver_name': forms.TextInput(attrs={'class': 'form-control'}),
            'driver_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'truck_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'delivery_type': forms.Select(attrs={'class': 'form-control'}),
            'hire_order': forms.Select(attrs={'class': 'form-control'}),
            'transport_request': forms.Select(attrs={'class': 'form-control'}),
            'inspection_notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'is_safe_for_transport': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hire_order'].queryset = HireOrder.objects.filter(status='APPROVED')
        self.fields['transport_request'].queryset = TransportRequest.objects.filter(status='APPROVED')

class DeliveryNoteItemForm(forms.ModelForm):
    class Meta:
        model = DeliveryNoteItem
        fields = ['material', 'quantity', 'condition', 'notes']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'condition': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 1, 'class': 'form-control'}),
            'material': forms.Select(attrs={'class': 'form-control'}),
        }

class DeliveryNoteForm(forms.ModelForm):
    class Meta:
        model = DeliveryNote
        fields = ['signed_by_driver', 'signed_by_scaffolder', 
                 'signed_by_security', 'signed_by_client']
        widgets = {
            'signed_by_driver': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'signed_by_scaffolder': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'signed_by_security': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'signed_by_client': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class GoodsReceivedVoucherForm(forms.ModelForm):
    class Meta:
        model = GoodsReceivedVoucher
        fields = ['delivery', 'hire_order', 'received_by', 'issued_by_client',
                 'all_items_received', 'discrepancy_notes']
        widgets = {
            'discrepancy_notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'delivery': forms.Select(attrs={'class': 'form-control'}),
            'hire_order': forms.Select(attrs={'class': 'form-control'}),
            'received_by': forms.Select(attrs={'class': 'form-control'}),
            'issued_by_client': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'all_items_received': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class GRVItemForm(forms.ModelForm):
    class Meta:
        model = GRVItem
        fields = ['material', 'quantity_expected', 'quantity_received', 
                 'condition_on_receipt', 'notes']
        widgets = {
            'quantity_expected': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'readonly': 'readonly'}),
            'quantity_received': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'condition_on_receipt': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 1, 'class': 'form-control'}),
            'material': forms.Select(attrs={'class': 'form-control'}),
        }

DeliveryNoteItemFormSet = forms.inlineformset_factory(
    DeliveryNote, DeliveryNoteItem, 
    form=DeliveryNoteItemForm,
    extra=1,
    can_delete=True
)

GRVItemFormSet = forms.inlineformset_factory(
    GoodsReceivedVoucher, GRVItem,
    form=GRVItemForm,
    extra=1,
    can_delete=True
)