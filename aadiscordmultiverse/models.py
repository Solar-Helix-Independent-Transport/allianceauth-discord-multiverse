import logging

from allianceauth.authentication.models import State
from allianceauth.eveonline.models import (EveAllianceInfo, EveCharacter,
                                           EveCorporationInfo, EveFactionInfo)
from allianceauth.groupmanagement.models import ReservedGroupName
from allianceauth.notifications import notify
from django.contrib.auth.models import Group, User
from django.db import models
from django.utils.translation import gettext_lazy
from requests.exceptions import HTTPError

from .discord_client import DiscordApiBackoff, DiscordClient, DiscordRoles
from .discord_client.helpers import match_or_create_roles_from_names
from .managers import DiscordManagedServerManager, MultiDiscordUserManager

logger = logging.getLogger(__name__)


class DiscordManagedServer(models.Model):

    objects = DiscordManagedServerManager()

    guild_id = models.BigIntegerField(
        primary_key=True,
        help_text='Guild ID on Discord'
    )

    server_name = models.CharField(
        max_length=32,
        default='',
        blank=True,
        db_index=True,
        help_text='Server Name'
    )

    sync_names = models.BooleanField(
        default=False,
        help_text='Sync Auth Main Name to Discord.'
    )

    class Meta:
        permissions = (
            ("access_discord_multiverse",
             "Can access the Discord Multiverse services"),
            ("access_all_discords",
             "Can access the All the Discord Multiverse servers"),
        )

    state_access = models.ManyToManyField(
        State,
        blank=True,
        help_text="States to whose members this server is available."

    )

    group_access = models.ManyToManyField(
        Group,
        blank=True,
        help_text="Groups to whose members this server is available."
    )

    character_access = models.ManyToManyField(
        EveCharacter,
        blank=True,
        help_text="Characters to which this server is available."
    )

    corporation_access = models.ManyToManyField(
        EveCorporationInfo,
        blank=True,
        help_text="Corporations to whose members this server is available."
    )

    alliance_access = models.ManyToManyField(
        EveAllianceInfo,
        blank=True,
        help_text="Alliances to whose members this server is available."
    )

    faction_access = models.ManyToManyField(
        EveFactionInfo,
        blank=True,
        help_text="Factions to whose members this server is available."
    )

    ignored_groups = models.ManyToManyField(
        Group,
        blank=True,
        help_text="Groups that will not be synced to this discord server.",
        related_name="dmv_ignored_groups"
    )


class MultiDiscordUser(models.Model):
    guild = models.ForeignKey(
        DiscordManagedServer,
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text='Auth user owning this Discord account'
    )
    uid = models.BigIntegerField(
        db_index=True,
        help_text='user\'s ID on Discord'
    )
    username = models.CharField(
        max_length=32,
        default='',
        blank=True,
        db_index=True,
        help_text='user\'s username on Discord'
    )
    discriminator = models.CharField(
        max_length=4,
        default='',
        blank=True,
        help_text='user\'s discriminator on Discord'
    )
    activated = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
        help_text='Date & time this service account was activated'
    )

    objects = MultiDiscordUserManager()

    def __str__(self):
        return f'{self.user.username} - {self.uid}[{self.guild_id}]'

    def __repr__(self):
        return f'{type(self).__name__}(user=\'{self.user}\', uid={self.uid})'

    def update_nickname(self, nickname: str = None) -> bool:
        """Update nickname with formatted name of main character

        Params:
        - nickname: optional nickname to be used instead of user's main

        Returns:
        - True on success
        - None if user is no longer a member of the Discord server
        - False on error or raises exception
        """
        if not nickname:
            nickname = MultiDiscordUser.objects.user_formatted_nick(
                self.user, self.guild)
        if nickname:
            client = MultiDiscordUser.objects._bot_client()
            success = client.modify_guild_member(
                guild_id=self.guild_id,
                user_id=self.uid,
                nick=nickname
            )
            if success:
                logger.info('Nickname for %s has been updated', self.user)
            else:
                logger.warning('Failed to update nickname for %s', self.user)
            return success

        else:
            return False

    def update_groups(self, state_name: str = None) -> bool:
        """update groups for a user based on his current group memberships.
        Will add or remove roles of a user as needed.

        Params:
        - state_name: optional state name to be used

        Returns:
        - True on success
        - None if user is no longer a member of the Discord server
        - False on error or raises exception
        """
        client = MultiDiscordUser.objects._bot_client()
        member_roles = self._determine_member_roles(client)
        if member_roles is None:
            return None
        return self._update_roles_if_needed(client, state_name, member_roles)

    def _determine_member_roles(self, client: DiscordClient) -> DiscordRoles:
        """Determine the roles of the current member / user."""
        member_info = client.guild_member(
            guild_id=self.guild_id, user_id=self.uid)
        if member_info is None:
            return None  # User is no longer a member
        guild_roles = DiscordRoles(client.guild_roles(guild_id=self.guild_id))
        logger.debug('Current guild roles: %s', guild_roles.ids())
        if 'roles' in member_info:
            if not guild_roles.has_roles(member_info['roles']):
                guild_roles = DiscordRoles(
                    client.guild_roles(guild_id=self.guild_id, use_cache=False)
                )
                if not guild_roles.has_roles(member_info['roles']):
                    raise RuntimeError(
                        'Member {} has unknown roles: {}'.format(
                            self.user,
                            set(member_info['roles']).difference(
                                guild_roles.ids())
                        )
                    )
            return guild_roles.subset(member_info['roles'])
        raise RuntimeError('member_info from %s is not valid' % self.user)

    def _update_roles_if_needed(
        self, client: DiscordClient, state_name: str, member_roles: DiscordRoles
    ) -> bool:
        """Update the roles of this member/user if needed."""
        requested_roles = match_or_create_roles_from_names(
            client=client,
            guild_id=self.guild_id,
            role_names=MultiDiscordUser.objects.user_group_names(
                user=self.user, groups_ignored=self.guild.ignored_groups.all(), state_name=state_name
            )
        )
        logger.debug(
            'Requested roles for user %s: %s', self.user, requested_roles.ids()
        )
        logger.debug('Current roles user %s: %s',
                     self.user, member_roles.ids())
        reserved_role_names = ReservedGroupName.objects.values_list(
            "name", flat=True)
        member_roles_reserved = member_roles.subset(
            role_names=reserved_role_names)
        member_roles_managed = member_roles.subset(managed_only=True)
        member_roles_persistent = member_roles_managed.union(
            member_roles_reserved)
        if requested_roles != member_roles.difference(member_roles_persistent):
            logger.debug('Need to update roles for user %s', self.user)
            new_roles = requested_roles.union(member_roles_persistent)
            success = client.modify_guild_member(
                guild_id=self.guild_id,
                user_id=self.uid,
                role_ids=list(new_roles.ids())
            )
            if success:
                logger.info('Roles for %s have been updated', self.user)
            else:
                logger.warning('Failed to update roles for %s', self.user)
            return success
        logger.info('No need to update roles for user %s', self.user)
        return True

    def update_username(self) -> bool:
        """Updates the username incl. the discriminator
        from the Discord server and saves it

        Returns:
        - True on success
        - None if user is no longer a member of the Discord server
        - False on error or raises exception
        """
        client = MultiDiscordUser.objects._bot_client()
        user_info = client.guild_member(
            guild_id=self.guild_id, user_id=self.uid)
        if user_info is None:
            success = None
        elif (
            user_info
            and 'user' in user_info
            and 'username' in user_info['user']
            and 'discriminator' in user_info['user']
        ):
            self.username = user_info['user']['username']
            self.discriminator = user_info['user']['discriminator']
            self.save()
            logger.info('Username for %s has been updated', self.user)
            success = True
        else:
            logger.warning('Failed to update username for %s', self.user)
            success = False
        return success

    def delete_user(
        self,
        notify_user: bool = False,
        is_rate_limited: bool = True,
        handle_api_exceptions: bool = False
    ) -> bool:
        """Deletes the Discount user both on the server and locally

        Params:
        - notify_user: When True will sent a notification to the user
        informing him about the deleting of his account
        - is_rate_limited: When False will disable default rate limiting (use with care)
        - handle_api_exceptions: When True method will return False
        when an API exception occurs

        Returns True when successful, otherwise False or raises exceptions
        Return None if user does no longer exist
        """
        try:
            _user = self.user
            client = MultiDiscordUser.objects._bot_client(
                is_rate_limited=is_rate_limited)
            success = client.remove_guild_member(
                guild_id=self.guild_id, user_id=self.uid
            )
            if success is not False:
                deleted_count, _ = self.delete()
                if deleted_count > 0:
                    if notify_user:
                        notify(
                            user=_user,
                            title=gettext_lazy('Discord Account Disabled'),
                            message=gettext_lazy(
                                'Your Discord account was disabled automatically '
                                'by Auth. If you think this was a mistake, '
                                'please contact an admin.'
                            ),
                            level='warning'
                        )
                    logger.info('Account for user %s was deleted.', _user)
                    return True
                else:
                    logger.debug(
                        'Account for user %s was already deleted.', _user)
                    return None

            else:
                logger.warning(
                    'Failed to remove user %s from the Discord server', _user
                )
                return False

        except (HTTPError, ConnectionError, DiscordApiBackoff) as ex:
            if handle_api_exceptions:
                logger.exception(
                    'Failed to remove user %s from Discord server: %s', self.user, ex
                )
                return False
            else:
                raise ex
