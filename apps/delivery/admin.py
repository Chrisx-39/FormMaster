from django.contrib import admin
from django.utils.html import format_html
from .models import *

class DeliveryNoteItemInline(admin.TabularInline):
    model = DeliveryNoteItem
    extra = 1

class GRVItemInline(admin.TabularInline):
    model = GRVItem
    extra = 1

@admin.register(TransportRequest)
class TransportRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'hire_order', 'requested_by', 'required_date', 
                   'status', 'truck_type_required', 'created_at')
    list_filter = ('status', 'truck_type_required', 'required_date', 'created_at')
    search_fields = ('request_number', 'hire_order__order_number', 
                    'requested_by__username', 'delivery_address')
    readonly_fields = ('request_number', 'requested_by', 'request_date', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('request_number', 'hire_order', 'requested_by', 'request_date')
        }),
        ('Delivery Details', {
            'fields': ('required_date', 'truck_type_required', 'delivery_address', 
                      'special_instructions')
        }),
        ('Approval Information', {
            'fields': ('approved_by', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.requested_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('delivery_number', 'hire_order', 'driver_name', 'truck_registration',
                   'departure_time', 'delivery_type', 'status', 'inspected_by')
    list_filter = ('delivery_type', 'status', 'departure_time', 'created_at')
    search_fields = ('delivery_number', 'hire_order__order_number', 'driver_name',
                    'truck_registration', 'delivery_address')
    readonly_fields = ('delivery_number', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('delivery_number', 'hire_order', 'transport_request', 'delivery_type')
        }),
        ('Transport Details', {
            'fields': ('driver_name', 'driver_phone', 'truck_registration',
                      'departure_time', 'arrival_time', 'delivery_address')
        }),
        ('Inspection Details', {
            'fields': ('inspected_by', 'inspection_notes', 'is_safe_for_transport')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.inspected_by:
            obj.inspected_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(DeliveryNote)
class DeliveryNoteAdmin(admin.ModelAdmin):
    list_display = ('note_number', 'delivery', 'issued_date', 'is_fully_signed',
                   'signed_by_client', 'created_at')
    list_filter = ('issued_date', 'signed_by_driver', 'signed_by_scaffolder',
                  'signed_by_security', 'signed_by_client')
    search_fields = ('note_number', 'delivery__delivery_number', 
                    'delivery__hire_order__order_number')
    readonly_fields = ('note_number', 'issued_date', 'created_at')
    inlines = [DeliveryNoteItemInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('note_number', 'delivery', 'issued_date', 'document')
        }),
        ('Signatures', {
            'fields': (('signed_by_driver', 'driver_signature_date'),
                      ('signed_by_scaffolder', 'scaffolder_signature_date'),
                      ('signed_by_security', 'security_signature_date'),
                      ('signed_by_client', 'client_signature_date'))
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def is_fully_signed(self, obj):
        return obj.is_fully_signed()
    is_fully_signed.boolean = True
    is_fully_signed.short_description = 'Fully Signed'

@admin.register(DeliveryNoteItem)
class DeliveryNoteItemAdmin(admin.ModelAdmin):
    list_display = ('delivery_note', 'material', 'quantity', 'condition', 'notes')
    list_filter = ('condition',)
    search_fields = ('delivery_note__note_number', 'material__name', 'notes')

@admin.register(GoodsReceivedVoucher)
class GoodsReceivedVoucherAdmin(admin.ModelAdmin):
    list_display = ('grv_number', 'delivery', 'hire_order', 'received_by',
                   'received_date', 'all_items_received', 'issued_by_client')
    list_filter = ('received_date', 'all_items_received', 'issued_by_client')
    search_fields = ('grv_number', 'delivery__delivery_number', 
                    'hire_order__order_number', 'received_by__username')
    readonly_fields = ('grv_number', 'received_date', 'created_at')
    inlines = [GRVItemInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('grv_number', 'delivery', 'hire_order')
        }),
        ('Receipt Details', {
            'fields': ('received_date', 'received_by', 'all_items_received',
                      'issued_by_client', 'discrepancy_notes', 'document')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(GRVItem)
class GRVItemAdmin(admin.ModelAdmin):
    list_display = ('grv', 'material', 'quantity_expected', 'quantity_received',
                   'condition_on_receipt', 'get_discrepancy')
    list_filter = ('condition_on_receipt',)
    search_fields = ('grv__grv_number', 'material__name', 'notes')
    
    def get_discrepancy(self, obj):
        return obj.get_discrepancy()
    get_discrepancy.short_description = 'Discrepancy'