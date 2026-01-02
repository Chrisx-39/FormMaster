from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from phonenumber_field.formfields import PhoneNumberField
from django_countries.widgets import CountrySelectWidget

from .models import *

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'name', 'trading_as', 'client_type', 'status',
            'contact_person', 'position', 'email', 'phone', 'alternate_phone', 'fax',
            'physical_address', 'postal_address', 'city', 'province', 'country', 'gps_coordinates',
            'registration_number', 'tax_number', 'vat_number', 'business_sector', 'year_established',
            'credit_limit', 'payment_terms', 'discount_rate',
            'account_manager', 'referred_by', 'relationship_start_date', 'notes',
            'client_contract', 'kyc_document', 'certificate_of_registration'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Client name'}),
            'trading_as': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Trading name'}),
            'client_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+263 xxx xxx xxx'}),
            'alternate_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+263 xxx xxx xxx'}),
            'fax': forms.TextInput(attrs={'class': 'form-control'}),
            'physical_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'postal_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.TextInput(attrs={'class': 'form-control'}),
            'country': CountrySelectWidget(attrs={'class': 'form-control'}),
            'gps_coordinates': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., -17.8252, 31.0335'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_number': forms.TextInput(attrs={'class': 'form-control'}),
            'vat_number': forms.TextInput(attrs={'class': 'form-control'}),
            'business_sector': forms.TextInput(attrs={'class': 'form-control'}),
            'year_established': forms.NumberInput(attrs={'class': 'form-control'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_terms': forms.Select(attrs={'class': 'form-control'}),
            'discount_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'account_manager': forms.Select(attrs={'class': 'form-control'}),
            'referred_by': forms.Select(attrs={'class': 'form-control'}),
            'relationship_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        help_texts = {
            'phone': 'Enter Zimbabwe phone number starting with +263',
            'alternate_phone': 'Optional alternate phone number',
            'gps_coordinates': 'Optional GPS coordinates for mapping',
            'credit_limit': 'Maximum credit allowed for this client (0 for no credit)',
            'discount_rate': 'Default discount percentage for this client',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter account managers to only FSM and HCE roles
        self.fields['account_manager'].queryset = User.objects.filter(
            role__in=['FSM', 'HCE', 'ADMIN']
        )
        # Filter referred_by to active clients
        self.fields['referred_by'].queryset = Client.objects.filter(status='ACTIVE')
        
        # Set initial relationship start date to today if new client
        if not self.instance.pk:
            self.fields['relationship_start_date'].initial = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate postal address
        if not cleaned_data.get('postal_address'):
            cleaned_data['postal_address'] = cleaned_data.get('physical_address', '')
        
        # Validate credit limit
        credit_limit = cleaned_data.get('credit_limit', 0)
        if credit_limit < 0:
            self.add_error('credit_limit', 'Credit limit cannot be negative.')
        
        # Validate discount rate
        discount_rate = cleaned_data.get('discount_rate', 0)
        if discount_rate < 0 or discount_rate > 100:
            self.add_error('discount_rate', 'Discount rate must be between 0 and 100.')
        
        return cleaned_data

class ClientContactForm(forms.ModelForm):
    class Meta:
        model = ClientContact
        fields = ['name', 'position', 'contact_type', 'email', 'phone', 'mobile', 'notes', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_type': forms.Select(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+263 xxx xxx xxx'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+263 xxx xxx xxx'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ClientSiteForm(forms.ModelForm):
    class Meta:
        model = ClientSite
        fields = ['site_name', 'site_code', 'address', 'city', 'province', 
                 'gps_coordinates', 'site_manager', 'site_phone', 
                 'is_active', 'is_main_site', 'notes']
        widgets = {
            'site_name': forms.TextInput(attrs={'class': 'form-control'}),
            'site_code': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.TextInput(attrs={'class': 'form-control'}),
            'gps_coordinates': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., -17.8252, 31.0335'}),
            'site_manager': forms.TextInput(attrs={'class': 'form-control'}),
            'site_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+263 xxx xxx xxx'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_main_site': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ClientDocumentForm(forms.ModelForm):
    class Meta:
        model = ClientDocument
        fields = ['document_type', 'name', 'description', 'document_file', 'valid_until', 'is_active']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'valid_until': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ClientNoteForm(forms.ModelForm):
    class Meta:
        model = ClientNote
        fields = ['note_type', 'subject', 'content', 'follow_up_date', 'priority']
        widgets = {
            'note_type': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }

class CreditNoteForm(forms.ModelForm):
    class Meta:
        model = CreditNote
        fields = ['client', 'invoice', 'amount', 'reason', 'valid_until', 'notes']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-control'}),
            'invoice': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'valid_until': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            # Set default valid until date (90 days from now)
            self.fields['valid_until'].initial = timezone.now().date() + timezone.timedelta(days=90)
    
    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise ValidationError('Credit note amount must be greater than zero.')
        return amount

class ClientRatingForm(forms.ModelForm):
    class Meta:
        model = ClientRating
        fields = ['rating_date', 'payment_timeliness', 'communication', 'cooperation',
                 'volume_of_business', 'profitability', 'comments']
        widgets = {
            'rating_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_timeliness': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'communication': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'cooperation': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'volume_of_business': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'profitability': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class BlacklistClientForm(forms.ModelForm):
    class Meta:
        model = ClientBlacklist
        fields = ['reason', 'notes', 'evidence_document']
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class ClientSearchForm(forms.Form):
    name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Client name...'})
    )
    
    client_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Client.CLIENT_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Client.CLIENT_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    city = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City...'})
    )
    
    account_manager = forms.ModelChoiceField(
        queryset=User.objects.filter(role__in=['FSM', 'HCE', 'ADMIN']),
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
    
    credit_status = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('LOW', 'Low Risk'),
            ('MODERATE', 'Moderate Risk'),
            ('HIGH', 'High Risk'),
            ('CRITICAL', 'Critical Risk'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class BalanceUpdateForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    transaction_type = forms.ChoiceField(
        choices=[
            ('INCREASE', 'Increase Balance'),
            ('DECREASE', 'Decrease Balance'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 
                                     'placeholder': 'Reason for balance update...'})
    )
    
    reference_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reference number...'})
    )

# FormSets
ClientContactFormSet = forms.inlineformset_factory(
    Client, ClientContact,
    form=ClientContactForm,
    extra=1,
    can_delete=True
)

ClientSiteFormSet = forms.inlineformset_factory(
    Client, ClientSite,
    form=ClientSiteForm,
    extra=1,
    can_delete=True
)