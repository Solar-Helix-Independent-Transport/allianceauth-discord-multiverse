import logging

from allianceauth import hooks
from allianceauth.services.hooks import ServicesHook, UrlHook
from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.template import TemplateDoesNotExist
from django.template.loader import get_template, render_to_string
from pytz import AmbiguousTimeError

from . import tasks, urls
from .models import DiscordManagedServer, MultiDiscordUser
from .urls import urlpatterns
from .utils import LoggerAddTag

logger = logging.getLogger(__name__)

# Default priority for single tasks like update group and sync nickname
SINGLE_TASK_PRIORITY = 3


class MultiDiscordService(ServicesHook):
    """Service for managing many Discord servers with a Single Auth"""
    def __init_subclass__(cls, gid, guild_name=None):
        super().__init_subclass__()
        cls.guild_id = gid
        cls.guild_name = guild_name

    def __init__(self):
        ServicesHook.__init__(self)
        self.urlpatterns = urlpatterns
        if hasattr(self, "guild_id"):
            self.name = f'dmv:{self.guild_name if self.guild_name else self.guild_id}'
        else:
            self.name = f'dmv'

        template = 'aadiscordmultiverse/dmv_service_ctrl.html'
        try:
            t = get_template("services/services_ctrl_base.html")
            template = 'aadiscordmultiverse/dmv_service_ctrl_bs5.html'
        except TemplateDoesNotExist:
            pass
        self.service_ctrl_template = template
        self.access_perm = 'aadiscordmultiverse.access_discord_multiverse'
        self.name_format = '{character_name}'

    def delete_user(self, user: User, notify_user: bool = False) -> None:
        if self.user_has_account(user):
            logger.debug(f"Removing {user} from {self.guild_id}")
            tasks.delete_user.apply_async(
                kwargs={'guild_id': self.guild_id,
                        'user_pk': user.pk, 'notify_user': notify_user},
                priority=SINGLE_TASK_PRIORITY
            )

    def render_services_ctrl(self, request):
        if self.user_has_account(request.user):
            user_has_account = True
            username = request.user.discord.username
            discriminator = request.user.discord.discriminator
            if username and discriminator:
                discord_username = f'{username}#{discriminator}'
            else:
                discord_username = ''
        else:
            discord_username = ''
            user_has_account = False

        return render_to_string(
            self.service_ctrl_template,
            {
                'server_name': MultiDiscordUser.objects.server_name(self.guild_id),
                "guild_id": self.guild_id,
                'user_has_account': user_has_account,
                'discord_username': discord_username
            },
            request=request
        )

    def service_active_for_user(self, user):
        has_perms = DiscordManagedServer.objects.visible_to(
            user).filter(guild_id=self.guild_id).exists()
        logger.debug(
            f"User {user} has {self.guild_id} permission: {has_perms}")
        return has_perms

    def sync_nickname(self, user):
        logger.debug(f"Syncing {user} nicknames on  {self.guild_id}")

        if self.user_has_account(user):
            tasks.update_nickname.apply_async(
                kwargs={
                    'guild_id': self.guild_id,
                    'user_pk': user.pk,
                    # since the new nickname is not yet in the DB we need to
                    # provide it manually to the task
                    'nickname': MultiDiscordUser.objects.user_formatted_nick(user)
                },
                priority=SINGLE_TASK_PRIORITY
            )

    def sync_nicknames_bulk(self, users: list):
        """Sync nickname for a list of users in bulk.
        Preferred over sync_nickname(), because it will not break the rate limit
        """
        logger.debug(
            'Syncing %s nicknames in bulk for %d users', self.name, len(users)
        )
        user_pks = [user.pk for user in users]
        tasks.update_nicknames_bulk.delay(user_pks, guild_id=self.guild_id)

    def update_all_groups(self):
        logger.debug('Update all %s groups called', self.name)
        tasks.update_all_groups.delay(guild_id=self.guild_id)

    def update_groups(self, user):
        logger.debug('Processing %s groups for %s', self.name, user)
        if self.user_has_account(user):
            tasks.update_groups.apply_async(
                args=[self.guild_id, ],
                kwargs={
                    'user_pk': user.pk,
                    # since state changes may not yet be in the DB we need to
                    # provide the new state name manually to the task
                    'state_name': user.profile.state.name
                },
                priority=SINGLE_TASK_PRIORITY
            )

    def update_groups_bulk(self, users: list):
        """Updates groups for a list of users in bulk.
        Preferred over update_groups(), because it will not break the rate limit
        """
        logger.debug(
            'Processing %s groups in bulk for %d users', self.name, len(users)
        )
        user_pks = [user.pk for user in users]
        tasks.update_groups_bulk.delay(user_pks, guild_id=self.guild_id)

    def user_has_account(self, user: User) -> bool:
        result = MultiDiscordUser.objects.user_has_account(
            user, guild_id=self.guild_id)
        if result:
            logger.debug('User %s has a Discord account', user)
        else:
            logger.debug('User %s does not have a Discord account', user)
        return result

    def validate_user(self, user):
        logger.debug('Validating user %s %s account', user, self.name)
        if self.user_has_account(user) and not self.service_active_for_user(user):
            self.delete_user(user, notify_user=True)


def add_del_callback(**kwargs):
    guild_add = list(DiscordManagedServer.objects.all(
    ).values_list("guild_id", flat=True))
    # Loop all services andd look for our hooks
    for h in hooks._hooks["services_hook"]:
        if isinstance(h(), MultiDiscordService):
            if h.guild_id in guild_add:
                guild_add.remove(h.guild_id)
            else:
                del (h)
    for gid in guild_add:
        print(f"GUILD ID {gid}")
        guild = DiscordManagedServer.objects.get(guild_id=gid)
        guild_class = type(
            f"MultiDiscordService{gid}", (MultiDiscordService,), {}, gid=guild.guild_id, guild_name=guild.server_name)

        hooks._hooks["services_hook"].append(guild_class)


post_save.connect(add_del_callback, sender=DiscordManagedServer)
post_delete.connect(add_del_callback, sender=DiscordManagedServer)
