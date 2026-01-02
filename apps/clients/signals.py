from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Client, ClientHistory, ClientNote

@receiver(post_save, sender=Client)
def log_client_creation(sender, instance, created, **kwargs):
    """Log client creation"""
    if created:
        ClientHistory.objects.create(
            client=instance,
            action='CREATED',
            performed_by=instance.created_by,
            description=f'Client created by {instance.created_by.get_full_name()}',
            new_value=instance.name
        )

@receiver(pre_save, sender=Client)
def log_client_changes(sender, instance, **kwargs):
    """Log client updates"""
    if instance.pk:
        try:
            old_instance = Client.objects.get(pk=instance.pk)
            
            # Check for status changes
            if old_instance.status != instance.status:
                ClientHistory.objects.create(
                    client=instance,
                    action='STATUS_CHANGE',
                    performed_by=instance.created_by,
                    description=f'Status changed from {old_instance.status} to {instance.status}',
                    old_value=old_instance.status,
                    new_value=instance.status
                )
            
            # Check for credit limit changes
            if old_instance.credit_limit != instance.credit_limit:
                ClientHistory.objects.create(
                    client=instance,
                    action='CREDIT_LIMIT_CHANGE',
                    performed_by=instance.created_by,
                    description=f'Credit limit changed from {old_instance.credit_limit} to {instance.credit_limit}',
                    old_value=str(old_instance.credit_limit),
                    new_value=str(instance.credit_limit)
                )
            
            # Check for balance changes
            if old_instance.current_balance != instance.current_balance:
                ClientHistory.objects.create(
                    client=instance,
                    action='BALANCE_UPDATE',
                    performed_by=instance.created_by,
                    description=f'Balance updated',
                    old_value=str(old_instance.current_balance),
                    new_value=str(instance.current_balance)
                )
                
        except Client.DoesNotExist:
            pass

@receiver(post_save, sender=ClientNote)
def log_note_creation(sender, instance, created, **kwargs):
    """Log client note creation"""
    if created:
        ClientHistory.objects.create(
            client=instance.client,
            action='NOTE_ADDED',
            performed_by=instance.created_by,
            description=f'Note added: {instance.subject}'
        )

@receiver(post_delete, sender=Client)
def log_client_deletion(sender, instance, **kwargs):
    """Log client deletion (if needed)"""
    # Note: This won't work if client is deleted with CASCADE
    pass