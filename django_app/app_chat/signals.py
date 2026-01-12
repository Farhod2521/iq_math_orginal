from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Message, ConversationParticipant


@receiver(post_save, sender=Message)
def increase_unread_count(sender, instance, created, **kwargs):
    if not created:
        return

    conversation = instance.conversation
    sender_user = instance.sender

    participants = ConversationParticipant.objects.filter(
        conversation=conversation
    ).exclude(user=sender_user)

    for participant in participants:
        participant.unread_count += 1
        participant.save(update_fields=["unread_count"])
