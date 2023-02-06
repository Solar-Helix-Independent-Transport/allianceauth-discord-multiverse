from allianceauth.services.hooks import get_extension_logger
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from .models import DiscordManagedServer
from .tasks import update_all

logger = get_extension_logger(__name__)


@receiver(post_save, sender=DiscordManagedServer)
def new_req(sender, instance, created, **kwargs):
    if not created:
        update_all.apply_async(args=[instance.guild_id], priority=4)
