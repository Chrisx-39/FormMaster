from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Delivery, DeliveryNote

@receiver(post_save, sender=Delivery)
def create_delivery_note_on_delivery_creation(sender, instance, created, **kwargs):
    """
    Automatically create a delivery note when a new delivery is created
    """
    if created and instance.hire_order:
        # Check if a delivery note already exists
        existing_note = DeliveryNote.objects.filter(delivery=instance).first()
        if not existing_note:
            DeliveryNote.objects.create(delivery=instance)