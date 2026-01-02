from django.contrib import admin
from django.utils.html import format_html
from .models import *

@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'document_type', 'is_active', 'is_default', 'created_at')
    list_filter = ('document_type', 'is_active', 'is_default', 'created_at')
    search_fields = ('name', 'document_type', 'html_template')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'document_type', 'is_active', 'is_default')
        }),
        ('Template Content', {
            'fields': ('template_file', 'html_template')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_number', 'document_type', 'status', 'generated_by', 
                   'generated_at', 'file_size_display', 'view_count', 'download_count')
    list_filter = ('document_type', 'status', 'generated_at', 'generated_by')
    search_fields = ('document_number', 'file_name', 'sent_to_email', 
                    'generated_by__username', 'generated_by__email')
    readonly_fields = ('document_number', 'generated_at', 'sent_at', 'viewed_at',
                      'signed_at', 'archived_at', 'view_count', 'download_count',
                      'last_viewed_at', 'last_downloaded_at', 'file_size')
    fieldsets = (
        ('Document Information', {
            'fields': ('document_number', 'document_type', 'status', 'template')
        }),
        ('Related Objects', {
            'fields': ('quotation', 'invoice', 'lease_agreement', 
                      'delivery_note', 'goods_received_voucher', 'request_for_quotation')
        }),
        ('File Information', {
            'fields': ('document_file', 'file_name', 'file_type', 'file_size')
        }),
        ('Status Tracking', {
            'fields': (('generated_by', 'generated_at'),
                      ('sent_to_email', 'sent_at'),
                      ('viewed_at', 'view_count', 'last_viewed_at'),
                      ('signed_at',),
                      ('archived_at',),
                      ('download_count', 'last_downloaded_at'))
        }),
    )
    
    def file_size_display(self, obj):
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.1f} KB"
        else:
            return f"{obj.file_size / (1024 * 1024):.1f} MB"
    file_size_display.short_description = 'File Size'

@admin.register(DocumentLog)
class DocumentLogAdmin(admin.ModelAdmin):
    list_display = ('document', 'action', 'performed_by', 'created_at', 'ip_address')
    list_filter = ('action', 'created_at', 'performed_by')
    search_fields = ('document__document_number', 'performed_by__username', 
                    'ip_address', 'notes')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Log Information', {
            'fields': ('document', 'action', 'performed_by')
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at')
        }),
    )

@admin.register(DocumentSetting)
class DocumentSettingAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'vat_number', 'tin_number', 'updated_at')
    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'company_address', 'company_phone',
                      'company_email', 'company_website', 'company_logo')
        }),
        ('Tax Information (Zimbabwe)', {
            'fields': ('vat_number', 'tin_number', 'vat_percentage')
        }),
        ('Document Defaults', {
            'fields': ('quotation_validity_days', 'invoice_due_days',
                      'default_currency', 'currency_symbol')
        }),
        ('Document Content', {
            'fields': ('footer_text', 'terms_and_conditions')
        }),
        ('Email Settings', {
            'fields': ('send_document_emails', 'email_subject_prefix', 
                      'email_signature')
        }),
        ('Archive Settings', {
            'fields': ('auto_archive_days', 'auto_delete_days')
        }),
        ('System Information', {
            'fields': ('updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one settings instance
        return not DocumentSetting.objects.exists()
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            # New instance
            obj.updated_by = request.user
        else:
            # Update existing instance
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_display', 'icon', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    readonly_fields = ()
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Display Settings', {
            'fields': ('color', 'icon', 'order')
        }),
    )
    
    def color_display(self, obj):
        return format_html(
            '<span style="display: inline-block; width: 20px; height: 20px; '
            'background-color: {}; border: 1px solid #ccc;"></span> {}',
            obj.color, obj.color
        )
    color_display.short_description = 'Color'

@admin.register(ArchivedDocument)
class ArchivedDocumentAdmin(admin.ModelAdmin):
    list_display = ('original_document', 'archived_by', 'archived_at', 'storage_location')
    list_filter = ('archived_at', 'archived_by')
    search_fields = ('original_document__document_number', 'archive_reason', 
                    'storage_location')
    readonly_fields = ('archived_at',)
    fieldsets = (
        ('Archive Information', {
            'fields': ('original_document', 'archived_by', 'archive_reason')
        }),
        ('Storage Information', {
            'fields': ('storage_location', 'archived_at')
        }),
    )