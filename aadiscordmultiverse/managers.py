import logging
from urllib.parse import urlencode

from allianceauth.eveonline.models import (EveAllianceInfo, EveCorporationInfo,
                                           EveFactionInfo)
from allianceauth.services.hooks import NameFormatter
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import models
from django.utils.timezone import now
from requests.exceptions import HTTPError
from requests_oauthlib import OAuth2Session

from .app_settings import (DISCORD_APP_ID, DISCORD_APP_SECRET,
                           DISCORD_BOT_TOKEN, DISCORD_CALLBACK_URL)
from .discord_client import DiscordClient
from .discord_client.exceptions import (DiscordApiBackoff,
                                        DiscordClientException)
from .discord_client.helpers import match_or_create_roles_from_names

logger = logging.getLogger(__name__)


class DiscordManagedServerQuerySet(models.QuerySet):
    def visible_to(self, user):
        # superusers/global get all visible
        if user.is_superuser or user.has_perm('aadiscordmultiverse.access_all_discords'):
            logger.debug(f'Returning all Servers for Global Perm {user}')
            return self

        if not user.has_perm('aadiscordmultiverse.access_discord_multiverse'):
            logger.debug(f'Returning No Servers for No Access Perm {user}')
            return self.none()

        try:
            main_character = user.profile.main_character
            assert main_character
            # build all accepted queries
            queries = []
            # States access everyone has a state
            queries.append(
                models.Q(
                    state_access__in=user.profile.state
                )
            )
            # Groups access, is ok if no groups.
            queries.append(
                models.Q(
                    group_access__in=user.groups.all()
                )
            )
            # ONLY on main char from here down
            # Character access
            queries.append(
                models.Q(
                    characters_access__in=main_character
                )
            )
            # Corp access
            queries.append(
                models.Q(
                    corporations_access__in=EveCorporationInfo.objects.filter(
                        main_character.corporation_id
                    )
                )
            )
            # Alliance access if part of an alliance
            if main_character.alliance_id:
                queries.append(
                    models.Q(
                        alliances_access__in=EveAllianceInfo.objects.filter(
                            alliance_id=main_character.alliance_id
                        )
                    )
                )
            # Faction access if part of a faction
            if main_character.faction_id:
                queries.append(
                    models.Q(
                        faction_access__in=EveFactionInfo.objects.filter(
                            faction_id=main_character.faction_id
                        )
                    )
                )

            logger.debug(
                f"{len(queries)} queries for {main_character}'s visible characters.")

            if settings.DEBUG:
                logger.debug(queries)

            # filter based on "OR" all queries
            query = queries.pop()
            for q in queries:
                query |= q
            return self.filter(query)
        except AssertionError:
            logger.debug(
                'User %s has no main character. Nothing visible.' % user)
            return self.none()


class DiscordManagedServerManager(models.Manager):
    """Manager for DiscordManagedServer"""

    def get_queryset(self):
        return DiscordManagedServerQuerySet(self.model, using=self._db)

    def visible_to(self, user):
        return self.get_queryset().visible_to(user)


class MultiDiscordUserManager(models.Manager):
    """Manager for MultiDiscordUser"""

    # full server admin
    BOT_PERMISSIONS = 0x00000008

    # get user ID, accept invite
    SCOPES = [
        'identify',
        'guilds.join',
    ]

    def add_user(
        self,
        user: User,
        authorization_code: str,
        is_rate_limited: bool = True,
        guild=None
    ) -> bool:
        """adds a new Discord user

        Params:
        - user: Auth user to join
        - authorization_code: authorization code returns from oauth
        - is_rate_limited: When False will disable default rate limiting (use with care)

        Returns: True on success, else False or raises exception
        """
        try:
            # TODO pull the guild config and confirm perms and settings
            nickname = self.user_formatted_nick(user, guild)
            group_names = self.user_group_names(
                user=user, groups_ignored=guild.ignored_groups.all(), state_name=user.profile.state.name)
            access_token = self._exchange_auth_code_for_token(
                authorization_code)
            user_client = DiscordClient(
                access_token, is_rate_limited=is_rate_limited)
            discord_user = user_client.current_user()
            user_id = discord_user['id']
            bot_client = self._bot_client(is_rate_limited=is_rate_limited)

            if group_names:
                role_ids = match_or_create_roles_from_names(
                    client=bot_client,
                    guild_id=guild.guild_id,
                    role_names=group_names
                ).ids()
            else:
                role_ids = None

            created = bot_client.add_guild_member(
                guild_id=guild.guild_id,
                user_id=user_id,
                access_token=access_token,
                role_ids=role_ids,
                nick=nickname
            )
            if created is not False:
                if created is None:
                    logger.debug(
                        "User %s with Discord ID %s is already a member. Forcing a Refresh",
                        user,
                        user_id,
                    )

                    # Force an update cause the discord API won't do it for us.
                    if role_ids:
                        role_ids = list(role_ids)

                    updated = bot_client.modify_guild_member(
                        guild_id=guild.guild_id,
                        user_id=user_id,
                        role_ids=role_ids,
                        nick=nickname
                    )

                    if not updated:
                        # Could not update the new user so fail.
                        logger.warning(
                            "Failed to add user %s with Discord ID %s to Discord server",
                            user,
                            user_id,
                        )
                        return False

                self.update_or_create(
                    user=user,
                    guild=guild,
                    defaults={
                        'uid': user_id,
                        'username': discord_user['username'][:32],
                        'discriminator': discord_user['discriminator'][:4],
                        'activated': now()
                    }
                )
                logger.info(
                    "Added user %s with Discord ID %s to Discord server", user, user_id
                )
                return True

            else:
                logger.warning(
                    "Failed to add user %s with Discord ID %s to Discord server",
                    user,
                    user_id,
                )
                return False

        except (HTTPError, ConnectionError, DiscordApiBackoff) as ex:
            logger.exception(
                'Failed to add user %s to Discord server: %s', user, ex
            )
            return False

    @staticmethod
    def user_formatted_nick(user: User, guild) -> str:
        """returns the name of the given users main character with name formatting
        or None if user has no main
        """

        if user.profile.main_character:
            from aadiscordmultiverse.auth_hooks import \
                MultiDiscordService  # nopep8

            tmp_type = type(
                f"MultiDiscordService{guild.guild_id}", (MultiDiscordService,), {}, gid=guild.guild_id, guild_name=guild.server_name)
            return NameFormatter(tmp_type(), user).format_name()
        else:
            return None

    @staticmethod
    def user_group_names(user: User, groups_ignored=Group.objects.none(), state_name: str = None) -> list:
        """returns list of group names plus state the given user is a member of"""
        if not state_name:
            state_name = user.profile.state.name
        group_names = (
            [group.name for group in user.groups.all().exclude(
                id__in=groups_ignored.values_list("id"))] + [state_name]
        )
        logger.debug(
            "Group names for roles updates of user %s are: %s", user, group_names
        )
        return group_names

    def user_has_account(self, user: User, guild_id: int) -> bool:
        """Returns True if the user has an Discord account, else False

        only checks locally, does not hit the API
        """
        if not isinstance(user, User):
            return False
        return self.filter(user=user, guild_id=guild_id).exists()

    @classmethod
    def generate_bot_add_url(cls) -> str:
        params = urlencode({
            'client_id': DISCORD_APP_ID,
            'scope': 'bot applications.commands',
            'permissions': str(cls.BOT_PERMISSIONS)

        })
        return f'{DiscordClient.OAUTH_BASE_URL}?{params}'

    def generate_oauth_redirect_url(self, guild_id) -> str:
        oauth = OAuth2Session(
            DISCORD_APP_ID, redirect_uri=DISCORD_CALLBACK_URL, scope=self.SCOPES
        )
        url, state = oauth.authorization_url(
            DiscordClient.OAUTH_BASE_URL, state=guild_id)
        return url

    @staticmethod
    def _exchange_auth_code_for_token(authorization_code: str) -> str:
        oauth = OAuth2Session(
            DISCORD_APP_ID, redirect_uri=DISCORD_CALLBACK_URL)
        token = oauth.fetch_token(
            DiscordClient.OAUTH_TOKEN_URL,
            client_secret=DISCORD_APP_SECRET,
            code=authorization_code
        )
        logger.debug("Received token from OAuth")
        return token['access_token']

    @classmethod
    def server_name(cls, gid, use_cache: bool = True) -> str:
        """returns the name of the current Discord server
        or an empty string if the name could not be retrieved

        Params:
        - use_cache: When set False will force an API call to get the server name
        """
        try:
            server_name = cls._bot_client().guild_name(
                guild_id=gid, use_cache=use_cache
            )
        except (HTTPError, DiscordClientException):
            server_name = ""
        except Exception:
            logger.warning(
                "Unexpected error when trying to retrieve the server name from Discord",
                exc_info=True
            )
            server_name = ""

        return server_name

    @classmethod
    def group_to_role(cls, group: Group) -> dict:
        """returns the Discord role matching the given Django group by name
        or an empty dict() if no matching role exist
        """
        return cls._bot_client().match_role_from_name(
            guild_id=self.guild_id, role_name=group.name
        )

    @staticmethod
    def _bot_client(is_rate_limited: bool = True) -> DiscordClient:
        """returns a bot client for access to the Discord API"""
        return DiscordClient(DISCORD_BOT_TOKEN, is_rate_limited=is_rate_limited)
