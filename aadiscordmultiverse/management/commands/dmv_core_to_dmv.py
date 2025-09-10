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
            "--createserver",
            action="store_true",
            help="Create the server if it doesnt already exists",
        )

        parser.add_argument(
            "--migrateusers",
            action="store_true",
            help="Migrate the discord users to the new server if it exists",
        )

        parser.add_argument(
            "--deleteusers",
            action="store_true",
            help="Delete old discord users if they have been migrated. requires --migrateusers",
        )

    def handle(self, *args, **options):
        create_server = options["createserver"]
        migrate_users = options["migrateusers"]
        delete_users = options["deleteusers"]

        if not create_server and not migrate_users:
            self.stderr.write(f"you need to define atleast one option... ")
            self.stderr.write(f"    --createserver - Create the server if it doesnt already exists")
            self.stderr.write(f"    --migrateusers - Migrate the discord users to the new server if it exists")
            self.stderr.write(f"    --deleteusers  - requires --migrateusers - Delete old discord users if they have been migrated")
            return

        if delete_users and not migrate_users:
            self.stderr.write(f"    --deleteusers  - requires --migrateusers")
            return

        self.stdout.write("Running checks!")
        # discord options
        DISCORD_GUILD_ID = getattr(settings, "DISCORD_GUILD_ID", False)
        DISCORD_SYNC_NAMES  = getattr(settings, "DISCORD_SYNC_NAMES", False)
        SITE_NAME = getattr(settings, "SITE_NAME", "")
        if DISCORD_GUILD_ID:
            self.stdout.write(f"Found Guild ID: {DISCORD_GUILD_ID} - Name Sync: {DISCORD_SYNC_NAMES}")
            servers = DiscordManagedServer.objects.filter(guild_id=DISCORD_GUILD_ID).exists()
            if not servers and create_server:
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

            else:
                self.stderr.write("Discord Guild ID already exists, we cant make it again.")

            if migrate_users:
                dmv = DiscordManagedServer.objects.get(
                        guild_id=DISCORD_GUILD_ID
                )
                discord_users = DiscordUser.objects.all()
                self.stdout.write(f"Starting migration of {discord_users.count()} users")
                if delete_users:
                    self.stdout.write(f"WILL delete the old discord service users")
                else:
                    self.stdout.write(f"WILL NOT delete the old discord service users. to do this re-run the script with `--deleteusers`")
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
                        if delete_users:
                            du.delete()
                    if delete_users:
                        du.delete()
                self.stdout.write(f"Finished migration of users, Skipped creation of {skipped} existing users")
            else:
                self.stdout.write(f"Skipping users, to migrate users use `--migrateusers`")
        else:
            self.stderr.write("Discord Guild ID not found in settings.")

        self.stdout.write(f"Completed migration, you can diable the inbuilt discord service now.")
        self.stdout.write(f"Please verify/adjust the configuration from the auth admin interface.")
