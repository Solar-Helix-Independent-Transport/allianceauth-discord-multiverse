from django.contrib.auth.models import Permission
from django.test import TestCase

from allianceauth.authentication.models import CharacterOwnership, State
from allianceauth.eveonline.models import (
    EveAllianceInfo, EveCharacter, EveCorporationInfo,
)
from allianceauth.tests.auth_utils import AuthUtils

from ..models import DiscordManagedServer


def create_char(char_id, char_name, corp=None):
    c = EveCharacter(character_id=char_id,
                     character_name=char_name,
                     corporation_id=corp.corporation_id,
                     corporation_name=corp.corporation_name,
                     corporation_ticker=corp.corporation_ticker)
    if corp.alliance:
        c.alliance_id = corp.alliance.alliance_id
        c.alliance_name = corp.alliance.alliance_name
        c.alliance_ticker = corp.alliance.alliance_ticker
    c.save()
    return c


class TestAccessPerms(TestCase):

    def setUp(cls):
        cls.corp1 = EveCorporationInfo.objects.create(corporation_id=123,
                                                      corporation_name='corporation.name1',
                                                      corporation_ticker='ABC',
                                                      ceo_id=1,
                                                      member_count=1
                                                      )
        cls.alli1 = EveAllianceInfo.objects.create(alliance_id=3,
                                                   alliance_name="alliance.names1",
                                                   alliance_ticker="TEST",
                                                   executor_corp_id=123
                                                   )
        cls.alli2 = EveAllianceInfo.objects.create(alliance_id=4,
                                                   alliance_name="alliance.names4",
                                                   alliance_ticker="TEST4",
                                                   executor_corp_id=3
                                                   )

        cls.corp2 = EveCorporationInfo.objects.create(corporation_id=2,
                                                      corporation_name='corporation.name2',
                                                      corporation_ticker='DEF',
                                                      ceo_id=2,
                                                      member_count=1,
                                                      alliance=cls.alli1
                                                      )

        cls.corp3 = EveCorporationInfo.objects.create(corporation_id=3,
                                                      corporation_name='corporation.name3',
                                                      corporation_ticker='GHI',
                                                      ceo_id=3,
                                                      member_count=1,
                                                      alliance=cls.alli2
                                                      )

        cls.corp4 = EveCorporationInfo.objects.create(corporation_id=4,
                                                      corporation_name='corporation.name4',
                                                      corporation_ticker='JKL',
                                                      ceo_id=4,
                                                      member_count=1,
                                                      alliance=cls.alli2
                                                      )

        cls.char1 = create_char(1, 'character.name1', corp=cls.corp1)
        cls.char2 = create_char(2, 'character.name2', corp=cls.corp1)
        cls.char3 = create_char(3, 'character.name3', corp=cls.corp2)
        cls.char4 = create_char(4, 'character.name4', corp=cls.corp2)
        cls.char5 = create_char(5, 'character.name5', corp=cls.corp3)
        cls.char6 = create_char(6, 'character.name6', corp=cls.corp3)
        cls.char7 = create_char(7, 'character.name7', corp=cls.corp4)
        cls.char8 = create_char(8, 'character.name8', corp=cls.corp4)
        cls.char9 = create_char(9, 'character.name9', corp=cls.corp2)
        cls.char10 = create_char(10, 'character.name10', corp=cls.corp2)

        cls.user1 = AuthUtils.create_user('User1')
        cls.user1.profile.main_character = cls.char1
        CharacterOwnership.objects.create(
            user=cls.user1, character=cls.char1, owner_hash="abc123")
        CharacterOwnership.objects.create(
            user=cls.user1, character=cls.char2, owner_hash="cba123")
        cls.user1.profile.save()
        cls.user1.profile.refresh_from_db()

        cls.user2 = AuthUtils.create_user('User2')
        cls.user2.profile.main_character = cls.char3
        CharacterOwnership.objects.create(
            user=cls.user2, character=cls.char3, owner_hash="cba321")
        cls.user2.profile.save()
        cls.user2.profile.refresh_from_db()

        cls.user3 = AuthUtils.create_user('User3')
        cls.user3.profile.main_character = cls.char5
        CharacterOwnership.objects.create(
            user=cls.user3, character=cls.char5, owner_hash="abc432")
        CharacterOwnership.objects.create(
            user=cls.user3, character=cls.char7, owner_hash="def432")
        cls.user3.profile.save()
        cls.user3.profile.refresh_from_db()

        cls.user4 = AuthUtils.create_user('User4')
        CharacterOwnership.objects.create(
            user=cls.user4, character=cls.char9, owner_hash="def432a")
        CharacterOwnership.objects.create(
            user=cls.user4, character=cls.char10, owner_hash="def432b")

        cls.access_perm = Permission.objects.get_by_natural_key(
            'access_discord_multiverse', 'aadiscordmultiverse', 'discordmanagedserver')
        cls.all_servers_perm = Permission.objects.get_by_natural_key(
            'access_all_discords', 'aadiscordmultiverse', 'discordmanagedserver')

        cls.server_1_no_perms_at_all = DiscordManagedServer.objects.create(
            guild_id=12345678,
            server_name="server 1 test",
            sync_names=True
        )

        cls.server_2_with_perms = DiscordManagedServer.objects.create(
            guild_id=87654321,
            server_name="server 2 test",
            sync_names=True
        )

    def test_no_perms(self):
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user1).count(), 0)
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user2).count(), 0)
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user3).count(), 0)
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user4).count(), 0)

    def test_all_perms(self):
        self.user1.user_permissions.add(self.access_perm)
        self.user1.user_permissions.add(self.all_servers_perm)

        self.user4.user_permissions.add(self.access_perm)
        self.user4.user_permissions.add(self.all_servers_perm)

        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user1).count(), 2)
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user2).count(), 0)
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user3).count(), 0)
        # No Main Character
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user4).count(), 0)

    def test_state_perms_u1(self):
        member = State.objects.get(name="Member")
        member.permissions.add(self.access_perm)
        member.member_characters.add(self.char1)  # main u1
        member.member_characters.add(self.char9)  # alt u4

        self.user1.refresh_from_db()
        self.user4.refresh_from_db()

        self.server_2_with_perms.state_access.add(member)

        self.assertIn(
            self.server_2_with_perms,
            DiscordManagedServer.objects.visible_to(self.user1)
        )

        self.assertNotIn(
            self.server_1_no_perms_at_all,
            DiscordManagedServer.objects.visible_to(self.user1)
        )

        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user2).count(), 0)
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user3).count(), 0)
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user4).count(), 0)

    def test_corp_perms_corp_1(self):
        guest = State.objects.get(name="Guest")
        guest.permissions.add(self.access_perm)

        self.server_2_with_perms.corporation_access.add(self.corp1)

        self.assertIn(
            self.server_2_with_perms,
            DiscordManagedServer.objects.visible_to(self.user1)
        )
        self.assertNotIn(
            self.server_1_no_perms_at_all,
            DiscordManagedServer.objects.visible_to(self.user1)
        )
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user2).count(), 0)
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user3).count(), 0)
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user4).count(), 0)

    def test_corp_perms_alli_1(self):
        guest = State.objects.get(name="Guest")
        guest.permissions.add(self.access_perm)

        self.server_2_with_perms.alliance_access.add(self.alli1)

        self.assertIn(
            self.server_2_with_perms,
            DiscordManagedServer.objects.visible_to(self.user2)
        )
        self.assertNotIn(
            self.server_1_no_perms_at_all,
            DiscordManagedServer.objects.visible_to(self.user2)
        )
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user1).count(), 0)
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user3).count(), 0)
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user4).count(), 0)

    def test_corp_perms_alli_1(self):
        guest = State.objects.get(name="Guest")
        guest.permissions.add(self.access_perm)

        self.server_2_with_perms.alliance_access.add(self.alli1)

        self.assertIn(
            self.server_2_with_perms,
            DiscordManagedServer.objects.visible_to(self.user2)
        )
        self.assertNotIn(
            self.server_1_no_perms_at_all,
            DiscordManagedServer.objects.visible_to(self.user2)
        )
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user1).count(), 0)
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user3).count(), 0)
        self.assertEqual(
            DiscordManagedServer.objects.visible_to(self.user4).count(), 0)


    def test_can_access_func_u1(self):
        member = State.objects.get(name="Member")
        member.permissions.add(self.access_perm)
        member.member_characters.add(self.char1)  # main u1
        member.member_characters.add(self.char9)  # alt u4

        self.user1.refresh_from_db()
        self.user4.refresh_from_db()

        self.server_2_with_perms.state_access.add(member)

        self.assertTrue(
            DiscordManagedServer.user_can_access_guild(self.user1, self.server_2_with_perms)
        )
        self.assertFalse(
            DiscordManagedServer.user_can_access_guild(self.user1, self.server_1_no_perms_at_all)
        )


    def test_can_access_func_u1_guild(self):
        member = State.objects.get(name="Member")
        member.permissions.add(self.access_perm)
        member.member_characters.add(self.char1)  # main u1
        member.member_characters.add(self.char9)  # alt u4

        self.user1.refresh_from_db()
        self.user4.refresh_from_db()

        self.server_2_with_perms.state_access.add(member)

        self.assertTrue(
            DiscordManagedServer.user_can_access_guild(self.user1, self.server_2_with_perms.guild_id)
        )
        self.assertFalse(
            DiscordManagedServer.user_can_access_guild(self.user1, self.server_1_no_perms_at_all.guild_id)
        )
