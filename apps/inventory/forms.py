from django import forms
from django.core.exceptions import ValidationError
from .models import Material, MaterialCategory, MaterialInspection

class MaterialCategoryForm(forms.ModelForm):
    class Meta:
        model = MaterialCategory
        fields = ['name', 'description', 'code']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
        }

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = [
            'category', 'name', 'code', 'description',
            'unit_of_measure', 'daily_hire_rate', 'replacement_cost',
            'total_quantity', 'minimum_stock_level', 'location'
        ]
        widgets = {
            'category': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3
            }),
            'unit_of_measure': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'daily_hire_rate': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.01'
            }),
            'replacement_cost': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.01'
            }),
            'total_quantity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'minimum_stock_level': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
        }
    
    def clean_code(self):
        code = self.cleaned_data['code']
        if self.instance.pk:
            if Material.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
                raise ValidationError('This material code is already in use.')
        else:
            if Material.objects.filter(code=code).exists():
                raise ValidationError('This material code is already in use.')
        return code
    
    def clean_total_quantity(self):
        total_quantity = self.cleaned_data['total_quantity']
        if total_quantity < 0:
            raise ValidationError('Total quantity cannot be negative.')
        return total_quantity
    
    def clean_minimum_stock_level(self):
        minimum_stock_level = self.cleaned_data['minimum_stock_level']
        if minimum_stock_level < 0:
            raise ValidationError('Minimum stock level cannot be negative.')
        return minimum_stock_level

class MaterialInspectionForm(forms.ModelForm):
    class Meta:
        model = MaterialInspection
        fields = ['condition', 'notes', 'is_safe_for_use', 'next_inspection_date']
        widgets = {
            'condition': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'Enter inspection notes...'
            }),
            'is_safe_for_use': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 text-blue-600 rounded focus:ring-blue-500'
            }),
            'next_inspection_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'type': 'date'
            }),
        }

class MaterialAdjustmentForm(forms.Form):
    ADJUSTMENT_CHOICES = [
        ('ADD', 'Add Stock'),
        ('REMOVE', 'Remove Stock'),
    ]
    
    adjustment_type = forms.ChoiceField(
        choices=ADJUSTMENT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Enter quantity'
        })
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
            'rows': 3,
            'placeholder': 'Enter reason for adjustment...'
        })
    )