"""This script is for functional testing of the Discord client with a Discord server

It will run single requests of the various functions to validate
that they actually work - excluding those that require Oauth, or does not work
with a bot token. The results can be also seen in a special log file.

This script is design to be run manually as unit test, e.g. by running the following:

python manage.py test
allianceauth.services.modules.discord.discord_self.client.tests.piloting_functionality

To make it work please set the below mentioned environment variables for your server.
Since this may cause lots of 429s we'd recommend NOT to use your
alliance Discord server for this.
"""

from uuid import uuid1
import os
from unittest import TestCase
from time import sleep

from .. import DiscordClient
from ...utils import set_logger_to_file

logger = set_logger_to_file(
    'allianceauth.services.modules.discord.discord_self.client.client', __file__
)

# Make sure to set these environnement variables for your Discord server and user
DISCORD_GUILD_ID = os.environ['DISCORD_GUILD_ID']
DISCORD_BOT_TOKEN = os.environ['DISCORD_BOT_TOKEN']
DISCORD_USER_ID = os.environ['DISCORD_USER_ID']

RATE_LIMIT_DELAY_SECS = 1


class TestDiscordApiLive(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logger.info('Live demo of the Discord API Client')
        cls.client = DiscordClient(DISCORD_BOT_TOKEN)

    def test_run_other_features(self):
        """runs features that have not been run in any of the other tests"""
        self.client.guild_infos(DISCORD_GUILD_ID)
        sleep(RATE_LIMIT_DELAY_SECS)

        self.client.guild_name(DISCORD_GUILD_ID)
        sleep(RATE_LIMIT_DELAY_SECS)

        self.client.match_or_create_role_from_name(DISCORD_GUILD_ID, 'Testrole')
        sleep(RATE_LIMIT_DELAY_SECS)

        self.client.match_or_create_roles_from_names(
            DISCORD_GUILD_ID, ['Testrole A', 'Testrole B']
        )
        sleep(RATE_LIMIT_DELAY_SECS)

    def test_create_and_remove_roles(self):
        # get base
        logger.info('guild_roles')
        expected = {role['id'] for role in self.client.guild_roles(DISCORD_GUILD_ID)}

        # add role
        role_name = 'my test role 12345678'
        logger.info('create_guild_role')
        new_role = self.client.create_guild_role(
            guild_id=DISCORD_GUILD_ID, role_name=role_name
        )
        sleep(RATE_LIMIT_DELAY_SECS)
        self.assertEqual(new_role['name'], role_name)

        # remove role again
        logger.info('delete_guild_role')
        self.client.delete_guild_role(
            guild_id=DISCORD_GUILD_ID, role_id=new_role['id']
        )
        sleep(RATE_LIMIT_DELAY_SECS)

        # verify it worked
        logger.info('guild_roles')
        role_ids = {role['id'] for role in self.client.guild_roles(DISCORD_GUILD_ID)}
        sleep(RATE_LIMIT_DELAY_SECS)
        self.assertSetEqual(role_ids, expected)

    def test_change_member_nick(self):
        # set new nick for user
        logger.info('modify_guild_member')
        new_nick = f'Testnick {uuid1().hex}'[:32]
        self.assertTrue(
            self.client.modify_guild_member(
                guild_id=DISCORD_GUILD_ID, user_id=DISCORD_USER_ID, nick=new_nick
            )
        )
        sleep(RATE_LIMIT_DELAY_SECS)

        # verify it is saved
        logger.info('guild_member')
        user = self.client.guild_member(DISCORD_GUILD_ID, DISCORD_USER_ID)
        sleep(RATE_LIMIT_DELAY_SECS)
        self.assertEqual(user['nick'], new_nick)

    def test_member_add_remove_roles(self):
        # create new guild role
        logger.info('create_guild_role')
        new_role = self.client.create_guild_role(
            guild_id=DISCORD_GUILD_ID, role_name='Special role 98765'
        )
        sleep(RATE_LIMIT_DELAY_SECS)
        new_role_id = new_role['id']

        # add to member
        logger.info('add_guild_member_role')
        self.assertTrue(
            self.client.add_guild_member_role(
                guild_id=DISCORD_GUILD_ID, user_id=DISCORD_USER_ID, role_id=new_role_id
            )
        )
        sleep(RATE_LIMIT_DELAY_SECS)

        # remove again
        logger.info('remove_guild_member_role')
        self.assertTrue(
            self.client.remove_guild_member_role(
                guild_id=DISCORD_GUILD_ID, user_id=DISCORD_USER_ID, role_id=new_role_id
            )
        )
        sleep(RATE_LIMIT_DELAY_SECS)
