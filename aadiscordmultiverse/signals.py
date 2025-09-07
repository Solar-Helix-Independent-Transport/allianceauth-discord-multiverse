from django.db.models.signals import m2m_changed, pre_save
from django.dispatch import receiver

from allianceauth.services.hooks import get_extension_logger

from .models import DiscordManagedServer
from .tasks import (
    check_all_users_in_guild, update_all_guild_user_groups,
    update_all_guild_user_nicks, update_all_guild_users_with_groups,
)

logger = get_extension_logger(__name__)


@receiver(m2m_changed, sender=DiscordManagedServer.included_groups.through)
def new_groups(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action in ["post_add", "post_remove"]:
        update_all_guild_users_with_groups(
            instance.guild_id,
            pk_set
        )


@receiver(pre_save, sender=DiscordManagedServer)
def model_update(sender, instance, raw, using, update_fields, **kwargs):
    try:
        old = sender.objects.get(pk = instance.pk)
        # update when the "Managed Groups" option is changed on or off
        if not instance.include_all_managed_groups == old.include_all_managed_groups:
            update_all_guild_user_groups(
                instance.guild_id,
            )

        # update when the "Sync Names" option is changed to on
        if instance.sync_names and not old.sync_names:
            update_all_guild_user_nicks(
                instance.guild_id,
            )
    except DiscordManagedServer.DoesNotExist:
        # new create
        pass


def perms_change(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
        Perms have chagned CHECK EVERYONE!
    """
    if action in ["post_remove"]:
        check_all_users_in_guild.delay(
            instance.guild_id
        )


# all the m2m's
m2m_changed.connect(perms_change, sender=DiscordManagedServer.state_access.through)
m2m_changed.connect(perms_change, sender=DiscordManagedServer.group_access.through)
m2m_changed.connect(perms_change, sender=DiscordManagedServer.character_access.through)
m2m_changed.connect(perms_change, sender=DiscordManagedServer.corporation_access.through)
m2m_changed.connect(perms_change, sender=DiscordManagedServer.alliance_access.through)
m2m_changed.connect(perms_change, sender=DiscordManagedServer.faction_access.through)
