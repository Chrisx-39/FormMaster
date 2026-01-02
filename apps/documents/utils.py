import os
import io
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import KeepTogether
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings

from .models import DocumentSetting

# Register fonts (if using custom fonts)
try:
    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
except:
    pass  # Use default fonts if custom fonts not available

def get_document_settings():
    """Get document settings or create default"""
    try:
        return DocumentSetting.objects.get(pk=1)
    except DocumentSetting.DoesNotExist:
        return DocumentSetting()

def format_currency(amount, settings=None):
    """Format currency amount according to settings"""
    if settings is None:
        settings = get_document_settings()
    
    if isinstance(amount, (Decimal, float, int)):
        return f"{settings.currency_symbol}{amount:,.2f}"
    return amount

def format_date(date):
    """Format date consistently"""
    if date:
        return date.strftime('%d %B %Y')
    return ''

def get_company_info():
    """Get company information for document headers"""
    settings = get_document_settings()
    return {
        'name': settings.company_name,
        'address': settings.company_address,
        'phone': settings.company_phone,
        'email': settings.company_email,
        'website': settings.company_website,
        'vat_number': settings.vat_number,
        'tin_number': settings.tin_number,
        'logo_path': settings.company_logo.path if settings.company_logo else None,
    }

def get_quotation_context(quotation):
    """Get context data for quotation generation"""
    company = get_company_info()
    client = quotation.client
    
    # Calculate validity date
    validity_date = quotation.date_prepared + timedelta(days=get_document_settings().quotation_validity_days)
    
    # Prepare line items
    line_items = []
    for item in quotation.items.all():
        line_items.append({
            'description': item.material.name,
            'quantity': item.quantity,
            'unit': item.material.unit_of_measure,
            'daily_rate': format_currency(item.daily_rate),
            'duration': item.duration_days,
            'total': format_currency(item.line_total),
        })
    
    context = {
        'company': company,
        'client': {
            'name': client.name,
            'contact_person': client.contact_person,
            'address': client.address,
            'phone': client.phone,
            'email': client.email,
        },
        'quotation': {
            'number': quotation.quotation_number,
            'date': format_date(quotation.date_prepared),
            'valid_until': format_date(validity_date),
            'prepared_by': quotation.prepared_by.get_full_name(),
            'approved_by': quotation.approved_by.get_full_name() if quotation.approved_by else '',
            'transport_cost': format_currency(quotation.transport_cost),
            'subtotal': format_currency(quotation.subtotal),
            'tax_amount': format_currency(quotation.tax_amount),
            'total_amount': format_currency(quotation.total_amount),
            'notes': quotation.notes,
        },
        'line_items': line_items,
        'settings': {
            'vat_percentage': get_document_settings().vat_percentage,
            'currency': get_document_settings().default_currency,
        },
        'generated_at': timezone.now().strftime('%d %B %Y %H:%M'),
    }
    
    return context

def get_invoice_context(invoice):
    """Get context data for invoice generation"""
    company = get_company_info()
    client = invoice.client
    
    # Calculate due date
    due_date = invoice.invoice_date + timedelta(days=get_document_settings().invoice_due_days)
    
    context = {
        'company': company,
        'client': {
            'name': client.name,
            'contact_person': client.contact_person,
            'address': client.address,
            'phone': client.phone,
            'email': client.email,
        },
        'invoice': {
            'number': invoice.invoice_number,
            'date': format_date(invoice.invoice_date),
            'due_date': format_date(due_date),
            'subtotal': format_currency(invoice.subtotal),
            'tax_amount': format_currency(invoice.tax_amount),
            'total_amount': format_currency(invoice.total_amount),
            'amount_paid': format_currency(invoice.amount_paid),
            'balance_due': format_currency(invoice.balance_due),
            'payment_status': invoice.get_payment_status_display(),
            'invoice_type': invoice.get_invoice_type_display(),
            'issued_by': invoice.issued_by.get_full_name(),
        },
        'hire_order': {
            'number': invoice.hire_order.order_number if invoice.hire_order else '',
            'start_date': format_date(invoice.hire_order.start_date) if invoice.hire_order else '',
            'end_date': format_date(invoice.hire_order.expected_return_date) if invoice.hire_order else '',
        },
        'settings': {
            'vat_percentage': get_document_settings().vat_percentage,
            'currency': get_document_settings().default_currency,
            'footer_text': get_document_settings().footer_text,
        },
        'generated_at': timezone.now().strftime('%d %B %Y %H:%M'),
    }
    
    return context

def get_lease_agreement_context(agreement):
    """Get context data for lease agreement generation"""
    company = get_company_info()
    client = agreement.client
    
    context = {
        'company': company,
        'client': {
            'name': client.name,
            'contact_person': client.contact_person,
            'address': client.address,
            'phone': client.phone,
            'email': client.email,
            'tax_id': client.tax_id,
        },
        'agreement': {
            'number': agreement.agreement_number,
            'date': format_date(timezone.now()),
            'start_date': format_date(agreement.start_date),
            'end_date': format_date(agreement.end_date),
            'duration_days': agreement.hire_duration_days,
            'late_return_penalty': format_currency(agreement.late_return_penalty_per_day),
            'fsm_signature': agreement.signed_by_fsm.get_full_name() if agreement.signed_by_fsm else '',
            'fsm_signature_date': format_date(agreement.fsm_signature_date),
            'client_signed': agreement.signed_by_client,
            'client_signature_date': format_date(agreement.client_signature_date),
        },
        'hire_order': {
            'number': agreement.hire_order.order_number,
            'total_amount': format_currency(agreement.hire_order.total_amount()),
        },
        'terms_and_conditions': agreement.terms_and_conditions or get_document_settings().terms_and_conditions,
        'generated_at': timezone.now().strftime('%d %B %Y %H:%M'),
    }
    
    return context

def get_delivery_note_context(delivery_note):
    """Get context data for delivery note generation"""
    company = get_company_info()
    delivery = delivery_note.delivery
    client = delivery.hire_order.client
    
    # Prepare items
    items = []
    for item in delivery_note.items.all():
        items.append({
            'material': item.material.name,
            'code': item.material.code,
            'quantity': item.quantity,
            'condition': item.get_condition_display(),
            'notes': item.notes,
        })
    
    context = {
        'company': company,
        'client': {
            'name': client.name,
            'contact_person': client.contact_person,
            'address': delivery.delivery_address,
            'phone': client.phone,
        },
        'delivery': {
            'number': delivery.delivery_number,
            'date': format_date(delivery.departure_time),
            'driver': delivery.driver_name,
            'driver_phone': delivery.driver_phone,
            'truck_registration': delivery.truck_registration,
            'departure_time': delivery.departure_time.strftime('%d %B %Y %H:%M'),
            'arrival_time': delivery.arrival_time.strftime('%d %B %Y %H:%M') if delivery.arrival_time else '',
            'type': delivery.get_delivery_type_display(),
        },
        'delivery_note': {
            'number': delivery_note.note_number,
            'issued_date': format_date(delivery_note.issued_date),
            'signed_by_driver': delivery_note.signed_by_driver,
            'signed_by_scaffolder': delivery_note.signed_by_scaffolder,
            'signed_by_security': delivery_note.signed_by_security,
            'signed_by_client': delivery_note.signed_by_client,
        },
        'order': {
            'number': delivery.hire_order.order_number,
            'project': delivery.hire_order.project_name,
            'site_location': delivery.hire_order.site_location,
        },
        'items': items,
        'signatures': {
            'driver': 'Driver' if delivery_note.signed_by_driver else 'Not Signed',
            'scaffolder': 'Scaffolder' if delivery_note.signed_by_scaffolder else 'Not Signed',
            'security': 'Security' if delivery_note.signed_by_security else 'Not Signed',
            'client': 'Client' if delivery_note.signed_by_client else 'Not Signed',
        },
        'generated_at': timezone.now().strftime('%d %B %Y %H:%M'),
    }
    
    return context

def get_grv_context(grv):
    """Get context data for Goods Received Voucher generation"""
    company = get_company_info()
    delivery = grv.delivery
    client = grv.hire_order.client
    
    # Prepare items
    items = []
    total_expected = 0
    total_received = 0
    
    for item in grv.items.all():
        discrepancy = item.quantity_expected - item.quantity_received
        items.append({
            'material': item.material.name,
            'code': item.material.code,
            'expected': item.quantity_expected,
            'received': item.quantity_received,
            'discrepancy': discrepancy,
            'condition': item.get_condition_on_receipt_display(),
            'notes': item.notes,
        })
        total_expected += item.quantity_expected
        total_received += item.quantity_received
    
    context = {
        'company': company,
        'client': {
            'name': client.name,
            'contact_person': client.contact_person,
            'address': client.address,
            'phone': client.phone,
        },
        'grv': {
            'number': grv.grv_number,
            'date': format_date(grv.received_date),
            'received_by': grv.received_by.get_full_name(),
            'issued_by_client': grv.issued_by_client,
            'all_items_received': grv.all_items_received,
            'discrepancy_notes': grv.discrepancy_notes,
        },
        'delivery': {
            'number': delivery.delivery_number,
            'date': format_date(delivery.arrival_time) if delivery.arrival_time else '',
        },
        'order': {
            'number': grv.hire_order.order_number,
        },
        'items': items,
        'totals': {
            'expected': total_expected,
            'received': total_received,
            'discrepancy': total_expected - total_received,
        },
        'generated_at': timezone.now().strftime('%d %B %Y %H:%M'),
    }
    
    return context

def get_rfq_context(rfq):
    """Get context data for Request for Quotation generation"""
    company = get_company_info()
    client = rfq.client
    
    # Prepare items
    items = []
    for item in rfq.items.all():
        items.append({
            'material': item.material.name,
            'code': item.material.code,
            'quantity': item.quantity_requested,
            'notes': item.notes,
        })
    
    context = {
        'company': company,
        'client': {
            'name': client.name,
            'contact_person': client.contact_person,
            'address': client.address,
            'phone': client.phone,
            'email': client.email,
        },
        'rfq': {
            'number': rfq.rfq_number,
            'date': format_date(rfq.received_date),
            'required_date': format_date(rfq.required_date),
            'hire_duration': rfq.hire_duration_days,
            'received_by': rfq.received_by.get_full_name(),
            'notes': rfq.notes,
        },
        'items': items,
        'generated_at': timezone.now().strftime('%d %B %Y %H:%M'),
    }
    
    return context

def get_sample_context(doc_type):
    """Get sample context for template preview"""
    company = get_company_info()
    
    sample_context = {
        'company': company,
        'client': {
            'name': 'Sample Client Company Ltd',
            'contact_person': 'John Doe',
            'address': '123 Sample Street, Harare, Zimbabwe',
            'phone': '+263 242 987654',
            'email': 'sample@client.co.zw',
            'tax_id': 'TAX123456789',
        },
        'generated_at': timezone.now().strftime('%d %B %Y %H:%M'),
        'settings': {
            'vat_percentage': 15.00,
            'currency': 'USD',
            'currency_symbol': '$',
        }
    }
    
    if doc_type == 'QUOTATION':
        sample_context.update({
            'quotation': {
                'number': 'QT-2024-001',
                'date': format_date(timezone.now()),
                'valid_until': format_date(timezone.now() + timedelta(days=30)),
                'prepared_by': 'Sample HCE',
                'approved_by': 'Sample FSM',
                'transport_cost': format_currency(500),
                'subtotal': format_currency(15000),
                'tax_amount': format_currency(2250),
                'total_amount': format_currency(17250),
                'notes': 'Sample quotation notes',
            },
            'line_items': [
                {
                    'description': 'Steel Scaffolding Frames',
                    'quantity': 100,
                    'unit': 'pieces',
                    'daily_rate': format_currency(5),
                    'duration': 30,
                    'total': format_currency(15000),
                }
            ],
        })
    
    elif doc_type == 'INVOICE':
        sample_context.update({
            'invoice': {
                'number': 'INV-2024-001',
                'date': format_date(timezone.now()),
                'due_date': format_date(timezone.now() + timedelta(days=30)),
                'subtotal': format_currency(15000),
                'tax_amount': format_currency(2250),
                'total_amount': format_currency(17250),
                'amount_paid': format_currency(17250),
                'balance_due': format_currency(0),
                'payment_status': 'Paid',
                'invoice_type': 'Advance Payment',
                'issued_by': 'Sample HCE',
            },
            'hire_order': {
                'number': 'OR-2024-001',
                'start_date': format_date(timezone.now()),
                'end_date': format_date(timezone.now() + timedelta(days=30)),
            },
        })
    
    elif doc_type == 'LEASE_AGREEMENT':
        sample_context.update({
            'agreement': {
                'number': 'LA-2024-001',
                'date': format_date(timezone.now()),
                'start_date': format_date(timezone.now()),
                'end_date': format_date(timezone.now() + timedelta(days=30)),
                'duration_days': 30,
                'late_return_penalty': format_currency(50),
                'fsm_signature': 'Sample FSM',
                'fsm_signature_date': format_date(timezone.now()),
                'client_signed': True,
                'client_signature_date': format_date(timezone.now()),
            },
            'hire_order': {
                'number': 'OR-2024-001',
                'total_amount': format_currency(17250),
            },
            'terms_and_conditions': 'Sample terms and conditions...',
        })
    
    return sample_context

def generate_pdf_from_template(template_name, context):
    """Generate PDF using Django templates"""
    # Render HTML template
    html_content = render_to_string(f'documents/templates/{template_name}.html', context)
    
    # Convert HTML to PDF (using reportlab)
    return generate_pdf_from_html(html_content)

def generate_pdf_from_html(html_content):
    """Generate PDF from HTML content"""
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Parse HTML and convert to flowables
    flowables = html_to_flowables(html_content)
    
    # Build PDF
    doc.build(flowables)
    
    buffer.seek(0)
    return buffer

def generate_pdf_from_template_html(template_html, context):
    """Generate PDF from template HTML string"""
    # Replace template variables
    for key, value in context.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                template_html = template_html.replace(f'{{{{{key}.{subkey}}}}}', str(subvalue))
        else:
            template_html = template_html.replace(f'{{{{{key}}}}}', str(value))
    
    # Generate PDF
    return generate_pdf_from_html(template_html)

def html_to_flowables(html_content):
    """Convert HTML to ReportLab flowables (simplified version)"""
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#2c3e50')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=12,
        textColor=colors.HexColor('#34495e')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    # Parse HTML and create flowables
    flowables = []
    
    # Split HTML into lines and process
    lines = html_content.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('<h1>'):
            text = line[4:-5]
            flowables.append(Paragraph(text, title_style))
        elif line.startswith('<h2>'):
            text = line[4:-5]
            flowables.append(Paragraph(text, heading_style))
        elif line.startswith('<p>'):
            text = line[3:-4]
            flowables.append(Paragraph(text, normal_style))
        else:
            flowables.append(Paragraph(line, normal_style))
    
    return flowables

def create_simple_pdf(content_dict, title="Document"):
    """Create a simple PDF document"""
    buffer = BytesIO()
    
    # Create canvas
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Set up coordinates
    margin = 2*cm
    y = height - margin
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, title)
    y -= 1.5*cm
    
    # Content
    c.setFont("Helvetica", 10)
    for key, value in content_dict.items():
        c.drawString(margin, y, f"{key}: {value}")
        y -= 0.5*cm
        
        if y < margin:  # New page
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - margin
    
    c.save()
    buffer.seek(0)
    return buffer

def send_document_email(document, recipient_email, subject, message, send_copy=False):
    """Send document via email"""
    # This is a placeholder - implement actual email sending
    # using Django's email framework or third-party service
    
    # TODO: Implement email sending
    # 1. Prepare email with document attachment
    # 2. Use company email settings
    # 3. Handle both HTML and plain text
    # 4. Track email delivery
    
    pass

def archive_old_documents():
    """Archive documents older than retention period"""
    settings = get_document_settings()
    archive_date = timezone.now() - timedelta(days=settings.auto_archive_days)
    
    documents_to_archive = GeneratedDocument.objects.filter(
        generated_at__lt=archive_date,
        status__in=['DRAFT', 'SENT', 'VIEWED', 'SIGNED']
    )
    
    for document in documents_to_archive:
        ArchivedDocument.objects.create(
            original_document=document,
            archive_reason='Auto-archived after retention period'
        )
        document.status = 'ARCHIVED'
        document.archived_at = timezone.now()
        document.save()
    
    return documents_to_archive.count()

def cleanup_archived_documents():
    """Delete archived documents older than deletion period"""
    settings = get_document_settings()
    delete_date = timezone.now() - timedelta(days=settings.auto_delete_days)
    
    archived_to_delete = ArchivedDocument.objects.filter(
        archived_at__lt=delete_date
    )
    
    count = archived_to_delete.count()
    
    # Delete the documents
    for archived in archived_to_delete:
        archived.original_document.delete()
        archived.delete()
    
    return count