from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import *

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('client_number', 'name', 'client_type', 'status', 
                   'city', 'credit_limit', 'current_balance', 'available_credit_display',
                   'account_manager', 'created_at')
    list_filter = ('client_type', 'status', 'city', 'province', 'country', 
                  'account_manager', 'created_at')
    search_fields = ('client_number', 'name', 'trading_as', 'contact_person',
                    'email', 'phone', 'tax_number', 'vat_number')
    readonly_fields = ('client_number', 'created_at', 'updated_at', 
                      'available_credit', 'credit_utilization', 'credit_status')
    fieldsets = (
        ('Basic Information', {
            'fields': ('client_number', 'name', 'trading_as', 'client_type', 'status')
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'position', 'email', 'phone', 
                      'alternate_phone', 'fax')
        }),
        ('Address Information', {
            'fields': ('physical_address', 'postal_address', 'city', 
                      'province', 'country', 'gps_coordinates')
        }),
        ('Business Information', {
            'fields': ('registration_number', 'tax_number', 'vat_number',
                      'business_sector', 'year_established')
        }),
        ('Financial Information', {
            'fields': ('credit_limit', 'current_balance', 'available_credit',
                      'credit_utilization', 'credit_status', 'payment_terms',
                      'discount_rate')
        }),
        ('Relationship Management', {
            'fields': ('account_manager', 'referred_by', 'relationship_start_date',
                      'notes')
        }),
        ('Documents', {
            'fields': ('client_contract', 'kyc_document', 'certificate_of_registration'),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('is_verified', 'verification_date'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def available_credit_display(self, obj):
        return f"${obj.available_credit:,.2f}"
    available_credit_display.short_description = 'Available Credit'
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(ClientContact)
class ClientContactAdmin(admin.ModelAdmin):
    list_display = ('client', 'name', 'position', 'contact_type', 'email', 
                   'phone', 'is_active')
    list_filter = ('contact_type', 'is_active', 'client')
    search_fields = ('name', 'email', 'phone', 'client__name')
    raw_id_fields = ('client',)

@admin.register(ClientSite)
class ClientSiteAdmin(admin.ModelAdmin):
    list_display = ('client', 'site_name', 'city', 'is_active', 'is_main_site')
    list_filter = ('city', 'province', 'is_active', 'is_main_site')
    search_fields = ('site_name', 'client__name', 'address')
    raw_id_fields = ('client',)

@admin.register(ClientDocument)
class ClientDocumentAdmin(admin.ModelAdmin):
    list_display = ('client', 'name', 'document_type', 'uploaded_by', 
                   'uploaded_at', 'valid_until', 'is_active', 'is_expired')
    list_filter = ('document_type', 'is_active', 'uploaded_at')
    search_fields = ('name', 'client__name', 'description')
    readonly_fields = ('uploaded_at', 'is_expired')
    raw_id_fields = ('client', 'uploaded_by')
    
    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Expired'

@admin.register(ClientNote)
class ClientNoteAdmin(admin.ModelAdmin):
    list_display = ('client', 'subject', 'note_type', 'priority', 
                   'created_by', 'created_at', 'is_resolved')
    list_filter = ('note_type', 'priority', 'is_resolved', 'created_at')
    search_fields = ('subject', 'content', 'client__name')
    readonly_fields = ('created_at', 'resolved_at')
    raw_id_fields = ('client', 'created_by', 'resolved_by')

@admin.register(ClientHistory)
class ClientHistoryAdmin(admin.ModelAdmin):
    list_display = ('client', 'action', 'performed_by', 'performed_at')
    list_filter = ('action', 'performed_at', 'performed_by')
    search_fields = ('client__name', 'description', 'performed_by__username')
    readonly_fields = ('performed_at',)
    raw_id_fields = ('client', 'performed_by')

@admin.register(CreditNote)
class CreditNoteAdmin(admin.ModelAdmin):
    list_display = ('credit_note_number', 'client', 'amount', 'issued_date',
                   'valid_until', 'status', 'applied_to_invoice')
    list_filter = ('status', 'issued_date', 'client')
    search_fields = ('credit_note_number', 'client__name', 'reason')
    readonly_fields = ('credit_note_number', 'issued_date', 'applied_date')
    raw_id_fields = ('client', 'invoice', 'issued_by', 'applied_by', 
                    'applied_to_invoice')

@admin.register(ClientRating)
class ClientRatingAdmin(admin.ModelAdmin):
    list_display = ('client', 'rating_date', 'overall_score', 'rating_category',
                   'rated_by')
    list_filter = ('rating_date', 'rated_by')
    search_fields = ('client__name', 'comments')
    readonly_fields = ('overall_score', 'rating_category')
    raw_id_fields = ('client', 'rated_by')

@admin.register(BlacklistReason)
class BlacklistReasonAdmin(admin.ModelAdmin):
    list_display = ('reason_code', 'description', 'severity', 'is_active')
    list_filter = ('severity', 'is_active')
    search_fields = ('reason_code', 'description')

@admin.register(ClientBlacklist)
class ClientBlacklistAdmin(admin.ModelAdmin):
    list_display = ('client', 'reason', 'blacklisted_by', 'blacklisted_at',
                   'is_active')
    list_filter = ('is_active', 'blacklisted_at', 'reason')
    search_fields = ('client__name', 'notes')
    readonly_fields = ('blacklisted_at',)
    raw_id_fields = ('client', 'reason', 'blacklisted_by')