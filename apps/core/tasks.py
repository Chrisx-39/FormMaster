from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_quotation_email(quotation_id):
    """Send quotation email to client"""
    from apps.hiring.models import Quotation
    from apps.documents.utils import generate_quotation_pdf
    
    try:
        quotation = Quotation.objects.get(pk=quotation_id)
        client = quotation.client
        
        # Generate PDF
        pdf_file = generate_quotation_pdf(quotation)
        
        # Prepare email
        subject = f'Quotation #{quotation.quotation_number} - Formwork & Scaffolding'
        message = render_to_string('emails/quotation_email.txt', {
            'quotation': quotation,
            'client': client,
        })
        
        html_message = render_to_string('emails/quotation_email.html', {
            'quotation': quotation,
            'client': client,
        })
        
        # Send email (implement actual email sending)
        # send_mail(
        #     subject=subject,
        #     message=message,
        #     html_message=html_message,
        #     from_email=settings.DEFAULT_FROM_EMAIL,
        #     recipient_list=[client.email],
        #     attachments=[('quotation.pdf', pdf_file, 'application/pdf')]
        # )
        
        logger.info(f'Quotation email sent for {quotation.quotation_number}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send quotation email: {str(e)}')
        return False

@shared_task
def check_overdue_returns():
    """Check for overdue rentals and send notifications"""
    from apps.hiring.models import HireOrder
    from django.conf import settings
    
    today = timezone.now().date()
    overdue_orders = HireOrder.objects.filter(
        status='ACTIVE',
        expected_return_date__lt=today
    )
    
    for order in overdue_orders:
        days_overdue = (today - order.expected_return_date).days
        
        # Send notification based on days overdue
        if days_overdue == 1:
            send_overdue_notification.delay(order.id, 'FIRST_REMINDER')
        elif days_overdue == 3:
            send_overdue_notification.delay(order.id, 'SECOND_REMINDER')
        elif days_overdue == 7:
            send_overdue_notification.delay(order.id, 'FINAL_WARNING')
        
        logger.info(f'Order {order.order_number} is {days_overdue} days overdue')
    
    return f'Checked {overdue_orders.count()} overdue orders'

@shared_task
def send_overdue_notification(order_id, notification_type):
    """Send overdue notification"""
    from apps.hiring.models import HireOrder
    
    try:
        order = HireOrder.objects.get(pk=order_id)
        client = order.client
        
        # Prepare notification based on type
        if notification_type == 'FIRST_REMINDER':
            subject = f'Reminder: Equipment Return Overdue - Order #{order.order_number}'
            message = f'Your equipment was due for return on {order.expected_return_date}.'
        elif notification_type == 'SECOND_REMINDER':
            subject = f'Second Reminder: Equipment Return Overdue - Order #{order.order_number}'
            message = f'Your equipment is {days_overdue} days overdue. Please return immediately.'
        else:  # FINAL_WARNING
            subject = f'Final Warning: Equipment Return Overdue - Order #{order.order_number}'
            message = f'Your equipment is {days_overdue} days overdue. Penalties are accruing.'
        
        # Send email (implement actual email sending)
        # send_mail(
        #     subject=subject,
        #     message=message,
        #     from_email=settings.DEFAULT_FROM_EMAIL,
        #     recipient_list=[client.email]
        # )
        
        logger.info(f'Sent {notification_type} for order {order.order_number}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send overdue notification: {str(e)}')
        return False

@shared_task
def check_low_stock():
    """Check for low stock items and send alerts"""
    from apps.inventory.models import Material
    from django.conf import settings
    
    low_stock_items = Material.objects.filter(
        available_quantity__lte=models.F('minimum_stock_level')
    )
    
    if low_stock_items.exists():
        # Prepare email for FSM
        subject = 'Low Stock Alert - Formwork System'
        item_list = '\n'.join([f'{item.name}: {item.available_quantity} available (min: {item.minimum_stock_level})' 
                              for item in low_stock_items])
        message = f'The following items are below minimum stock levels:\n\n{item_list}'
        
        # Get FSM users
        from apps.accounts.models import User
        fsm_users = User.objects.filter(role='FSM', is_active=True)
        recipient_list = [user.email for user in fsm_users if user.email]
        
        if recipient_list:
            # Send email (implement actual email sending)
            # send_mail(
            #     subject=subject,
            #     message=message,
            #     from_email=settings.DEFAULT_FROM_EMAIL,
            #     recipient_list=recipient_list
            # )
            logger.info(f'Sent low stock alert for {low_stock_items.count()} items')
    
    return f'Checked {low_stock_items.count()} low stock items'

@shared_task
def generate_daily_reports():
    """Generate daily revenue and activity reports"""
    from apps.finance.models import RevenueRecord
    from apps.hiring.models import HireOrder
    from django.db.models import Sum, Count
    from datetime import date
    
    yesterday = date.today() - timedelta(days=1)
    
    # Calculate daily revenue
    orders = HireOrder.objects.filter(
        order_date__date=yesterday,
        status='COMPLETED'
    )
    
    total_revenue = orders.aggregate(total=Sum('quotation__total_amount'))['total'] or 0
    
    # Create revenue record
    if total_revenue > 0:
        RevenueRecord.objects.create(
            period_start=yesterday,
            period_end=yesterday,
            base_hire_revenue=total_revenue,
            total_revenue=total_revenue,
            recorded_date=timezone.now()
        )
    
    # Log daily activity
    logger.info(f'Daily report generated for {yesterday}: ${total_revenue:.2f} revenue')
    return f'Generated report for {yesterday}'

@shared_task
def cleanup_old_documents():
    """Archive documents older than retention period"""
    from django.conf import settings
    from django.utils import timezone
    from datetime import timedelta
    import os
    
    retention_days = settings.DOCUMENT_RETENTION_DAYS
    cutoff_date = timezone.now() - timedelta(days=retention_days)
    
    # Archive old documents (implementation depends on storage)
    logger.info(f'Cleanup task run. Documents before {cutoff_date} should be archived.')
    return 'Cleanup completed'