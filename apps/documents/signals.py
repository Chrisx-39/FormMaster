from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import GeneratedDocument, DocumentLog, DocumentSetting
from .utils import archive_old_documents, cleanup_archived_documents

@receiver(post_save, sender=GeneratedDocument)
def log_document_creation(sender, instance, created, **kwargs):
    """Log document creation"""
    if created:
        DocumentLog.objects.create(
            document=instance,
            action='GENERATED',
            performed_by=instance.generated_by,
            notes='Document created'
        )

@receiver(post_save, sender=GeneratedDocument)
def update_document_status_log(sender, instance, **kwargs):
    """Log status changes"""
    if instance.pk:
        try:
            old_instance = GeneratedDocument.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                DocumentLog.objects.create(
                    document=instance,
                    action='UPDATED',
                    performed_by=instance.generated_by,
                    notes=f'Status changed from {old_instance.status} to {instance.status}'
                )
        except GeneratedDocument.DoesNotExist:
            pass

@receiver(pre_delete, sender=GeneratedDocument)
def log_document_deletion(sender, instance, **kwargs):
    """Log document deletion"""
    DocumentLog.objects.create(
        document=instance,
        action='DELETED',
        notes='Document deleted from system'
    )

@receiver(post_save, sender=DocumentSetting)
def update_document_settings_log(sender, instance, **kwargs):
    """Log document settings changes"""
    if instance.updated_by:
        # This would be logged elsewhere, but included for completeness
        pass