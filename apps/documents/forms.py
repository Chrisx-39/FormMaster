from django import forms
from django.core.exceptions import ValidationError
from .models import DocumentTemplate, GeneratedDocument, DocumentSetting, DocumentCategory
from apps.hiring.models import Quotation, RequestForQuotation
from apps.finance.models import Invoice
from apps.delivery.models import DeliveryNote, GoodsReceivedVoucher

class DocumentTemplateForm(forms.ModelForm):
    class Meta:
        model = DocumentTemplate
        fields = ['name', 'document_type', 'template_file', 'html_template', 'is_active', 'is_default']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter template name'}),
            'document_type': forms.Select(attrs={'class': 'form-control'}),
            'html_template': forms.Textarea(attrs={'class': 'form-control', 'rows': 15, 
                                                  'placeholder': 'HTML template with variables...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'html_template': 'Use variables like {{client.name}}, {{quotation.total_amount}}, etc.',
        }

class DocumentSettingForm(forms.ModelForm):
    class Meta:
        model = DocumentSetting
        fields = '__all__'
        exclude = ['updated_at', 'updated_by']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'company_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'company_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'company_website': forms.URLInput(attrs={'class': 'form-control'}),
            'vat_number': forms.TextInput(attrs={'class': 'form-control'}),
            'tin_number': forms.TextInput(attrs={'class': 'form-control'}),
            'vat_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'quotation_validity_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'invoice_due_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'default_currency': forms.TextInput(attrs={'class': 'form-control'}),
            'currency_symbol': forms.TextInput(attrs={'class': 'form-control'}),
            'footer_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'terms_and_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'send_document_emails': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_subject_prefix': forms.TextInput(attrs={'class': 'form-control'}),
            'email_signature': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'auto_archive_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'auto_delete_days': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class DocumentCategoryForm(forms.ModelForm):
    class Meta:
        model = DocumentCategory
        fields = ['name', 'description', 'color', 'icon', 'order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 
                                          'placeholder': 'fas fa-file-invoice'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class DocumentSearchForm(forms.Form):
    document_type = forms.ChoiceField(
        choices=[('', 'All Types')] + DocumentTemplate.DOCUMENT_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + GeneratedDocument.DOCUMENT_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search...'})
    )

class SendDocumentForm(forms.Form):
    recipient_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'recipient@example.com'})
    )
    subject = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        required=False
    )
    send_copy_to_sender = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

class BulkDocumentActionForm(forms.Form):
    ACTION_CHOICES = [
        ('archive', 'Archive Selected'),
        ('delete', 'Delete Selected'),
        ('send', 'Send Selected by Email'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    document_ids = forms.CharField(
        widget=forms.HiddenInput()
    )