from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand

from allianceauth.authentication.models import State
from allianceauth.eveonline.models import (
    EveAllianceInfo, EveCharacter, EveCorporationInfo, EveFactionInfo,
)
from allianceauth.services.modules.discord.models import DiscordUser

from ...models import DiscordManagedServer, MultiDiscordUser


class Command(BaseCommand):
    help = 'Convert the inbuilt Discord service to a DMV managed service'

    def add_arguments(self, parser):

        parser.add_argument(
            "--skipchecks",
            action="store_true",
            help="Skip the server already exists checks",
        )

    def handle(self, *args, **options):
        skip_checks = options["skipchecks"]
        self.stdout.write("Running checks!")
        # discord options
        DISCORD_GUILD_ID = getattr(settings, "DISCORD_GUILD_ID", False)
        DISCORD_SYNC_NAMES  = getattr(settings, "DISCORD_SYNC_NAMES", False)
        SITE_NAME = getattr(settings, "SITE_NAME", "")
        if DISCORD_GUILD_ID:
            self.stdout.write(f"Found Guild ID: {DISCORD_GUILD_ID} - Name Sync: {DISCORD_SYNC_NAMES}")
            servers = DiscordManagedServer.objects.filter(guild_id=DISCORD_GUILD_ID).exists()
            if not servers:
                self.stdout.write(f"Creating Guild with ID: {DISCORD_GUILD_ID} - Name Sync: {DISCORD_SYNC_NAMES}")
                name = f"{SITE_NAME} Discord"
                perm = Permission.objects.get(codename="access_discord")
                perm_dmv = Permission.objects.get(codename="access_discord_multiverse")

                states = State.objects.filter(permissions__in=[perm])
                groups = Group.objects.filter(permissions__in=[perm])

                dmv = DiscordManagedServer.objects.create(
                    guild_id=DISCORD_GUILD_ID,
                    server_name=name,
                    sync_names=DISCORD_SYNC_NAMES,
                    include_all_managed_groups=True,
                )
                dmv.included_groups.set(Group.objects.all())

                self.stdout.write(f"Attempting to sync permissions....")
                if states.exists():
                    self.stdout.write(f"Adding perms for {states.count()} found states to the new server")
                    dmv.state_access.set(states)
                    for state in states:
                        state.permissions.add(perm_dmv)

                if groups.exists():
                    self.stdout.write(f"Adding perms for {groups.count()} found groups to the new server")
                    dmv.group_access.set(groups)
                    for group in groups:
                        group.permissions.add(perm_dmv)

            elif not skip_checks:
                self.stderr.write("Discord Guild ID already exists. use `--skipchecks` to force the users over.")
                return

            discord_users = DiscordUser.objects.all()
            self.stdout.write(f"Starting migration of {discord_users.count()} users")
            skipped=0
            for du in discord_users:
                dmvu = MultiDiscordUser.objects.filter(
                    guild_id=DISCORD_GUILD_ID,
                    uid=du.uid
                )
                if not dmvu.exists():
                    MultiDiscordUser.objects.create(
                        guild=dmv,
                        user=du.user,
                        uid=du.uid,
                        username=du.username,
                        discriminator=du.discriminator,
                        activated=du.activated
                    )
                else:
                    skipped += 1
                du.delete()
            self.stdout.write(f"Finished Migration of users, Skipped {skipped} users")
        else:
            self.stderr.write("Discord Guild ID not found in settings.")
        self.stdout.write(f"Completed Migration, you can diable the inbuilt discord service now. Please verify that the configuration is correct from the auth admin interface.")
