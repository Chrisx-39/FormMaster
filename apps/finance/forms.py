from django import forms
from django.forms import ModelForm
from django.utils import timezone

from .models import Invoice, Payment, Expense


# =========================
# INVOICE FORM
# =========================
class InvoiceForm(ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'hire_order',
            'client',
            'invoice_type',
            'due_date',
            'subtotal',
            'tax_amount',
            'total_amount',
            'notes',
            'document',
        ]
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()

        subtotal = cleaned_data.get('subtotal') or 0
        tax_amount = cleaned_data.get('tax_amount') or 0
        total_amount = cleaned_data.get('total_amount') or 0

        # Auto-calculate totals if missing
        if subtotal and not tax_amount:
            tax_amount = subtotal * 0.15
            cleaned_data['tax_amount'] = tax_amount

        if subtotal and not total_amount:
            cleaned_data['total_amount'] = subtotal + tax_amount

        return cleaned_data


# =========================
# PAYMENT FORM
# =========================
class PaymentForm(ModelForm):
    class Meta:
        model = Payment
        fields = [
            'invoice',
            'payment_date',
            'amount',
            'payment_method',
            'reference_number',
            'notes',
        ]
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError("Payment amount must be greater than zero.")
        return amount


# =========================
# EXPENSE FORM
# =========================
class ExpenseForm(ModelForm):
    class Meta:
        model = Expense
        fields = [
            'date',
            'category',
            'description',
            'amount',
            'vendor',
            'invoice_reference',
            'payment_method',
            'receipt',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError("Expense amount must be greater than zero.")
        return amount
