from unittest import TestCase

from . import (
    ROLE_ALPHA,
    ROLE_BRAVO,
    ROLE_CHARLIE,
    ROLE_CHARLIE_2,
    ROLE_MIKE,
    ALL_ROLES,
    create_role
)
from .. import DiscordRoles


MODULE_PATH = 'allianceauth.services.modules.discord.discord_client.client'


class TestDiscordRoles(TestCase):

    def setUp(self):
        self.all_roles = DiscordRoles(ALL_ROLES)

    def test_can_create_simple(self):
        roles_raw = [ROLE_ALPHA]
        roles = DiscordRoles(roles_raw)
        self.assertListEqual(list(roles), roles_raw)

    def test_can_create_empty(self):
        roles_raw = []
        roles = DiscordRoles(roles_raw)
        self.assertListEqual(list(roles), [])

    def test_raises_exception_if_roles_raw_of_wrong_type(self):
        with self.assertRaises(TypeError):
            DiscordRoles({'id': 1})

    def test_raises_exception_if_list_contains_non_dict(self):
        roles_raw = [ROLE_ALPHA, 'not_valid']
        with self.assertRaises(TypeError):
            DiscordRoles(roles_raw)

    def test_raises_exception_if_invalid_role_1(self):
        roles_raw = [{'name': 'alpha', 'managed': False}]
        with self.assertRaises(ValueError):
            DiscordRoles(roles_raw)

    def test_raises_exception_if_invalid_role_2(self):
        roles_raw = [{'id': 1, 'managed': False}]
        with self.assertRaises(ValueError):
            DiscordRoles(roles_raw)

    def test_raises_exception_if_invalid_role_3(self):
        roles_raw = [{'id': 1, 'name': 'alpha'}]
        with self.assertRaises(ValueError):
            DiscordRoles(roles_raw)

    def test_roles_are_equal(self):
        roles_a = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        roles_b = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        self.assertEqual(roles_a, roles_b)

    def test_roles_are_not_equal(self):
        roles_a = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        roles_b = DiscordRoles([ROLE_ALPHA])
        self.assertNotEqual(roles_a, roles_b)

    def test_different_objects_are_not_equal(self):
        roles_a = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        self.assertFalse(roles_a == "invalid")

    def test_len(self):
        self.assertEqual(len(self.all_roles), 4)

    def test_contains(self):
        self.assertTrue(1 in self.all_roles)
        self.assertFalse(99 in self.all_roles)

    def test_sanitize_role_name(self):
        role_name_input = 'x' * 110
        role_name_expected = 'x' * 100
        result = DiscordRoles.sanitize_role_name(role_name_input)
        self.assertEqual(result, role_name_expected)

    def test_objects_are_hashable(self):
        roles_a = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        roles_b = DiscordRoles([ROLE_BRAVO, ROLE_ALPHA])
        roles_c = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO, ROLE_MIKE])
        self.assertIsNotNone(hash(roles_a))
        self.assertEqual(hash(roles_a), hash(roles_b))
        self.assertNotEqual(hash(roles_a), hash(roles_c))

    def test_create_from_matched_roles(self):
        matched_roles = [
            (ROLE_ALPHA, True),
            (ROLE_BRAVO, False)
        ]
        roles = DiscordRoles.create_from_matched_roles(matched_roles)
        self.assertSetEqual(roles.ids(), {1, 2})


class TestIds(TestCase):

    def setUp(self):
        self.all_roles = DiscordRoles(ALL_ROLES)

    def test_return_role_ids_default(self):
        result = self.all_roles.ids()
        expected = {1, 2, 3, 13}
        self.assertSetEqual(result, expected)

    def test_return_role_ids_empty(self):
        roles = DiscordRoles([])
        self.assertSetEqual(roles.ids(), set())


class TestSubset(TestCase):

    def setUp(self):
        self.all_roles = DiscordRoles(ALL_ROLES)

    def test_ids_only(self):
        role_ids = {1, 3}
        roles_subset = self.all_roles.subset(role_ids)
        expected = {1, 3}
        self.assertSetEqual(roles_subset.ids(), expected)

    def test_ids_as_string_work_too(self):
        role_ids = {'1', '3'}
        roles_subset = self.all_roles.subset(role_ids)
        expected = {1, 3}
        self.assertSetEqual(roles_subset.ids(), expected)

    def test_managed_only(self):
        roles = self.all_roles.subset(managed_only=True)
        expected = {13}
        self.assertSetEqual(roles.ids(), expected)

    def test_ids_and_managed_only(self):
        role_ids = {1, 3, 13}
        roles_subset = self.all_roles.subset(role_ids, managed_only=True)
        expected = {13}
        self.assertSetEqual(roles_subset.ids(), expected)

    def test_ids_are_empty(self):
        roles = self.all_roles.subset([])
        expected = set()
        self.assertSetEqual(roles.ids(), expected)

    def test_no_parameters(self):
        roles = self.all_roles.subset()
        expected = {1, 2, 3, 13}
        self.assertSetEqual(roles.ids(), expected)

    def test_should_return_role_names_only(self):
        # given
        all_roles = DiscordRoles([
            ROLE_ALPHA, ROLE_BRAVO, ROLE_CHARLIE, ROLE_MIKE, ROLE_CHARLIE_2
        ])
        # when
        roles = all_roles.subset(role_names={"bravo", "charlie"})
        # then
        self.assertSetEqual(roles.ids(), {2, 3, 4})


class TestHasRoles(TestCase):

    def setUp(self):
        self.all_roles = DiscordRoles(ALL_ROLES)

    def test_true_if_all_roles_exit(self):
        self.assertTrue(self.all_roles.has_roles([1, 2]))

    def test_true_if_all_roles_exit_str(self):
        self.assertTrue(self.all_roles.has_roles(['1', '2']))

    def test_false_if_role_does_not_exit(self):
        self.assertFalse(self.all_roles.has_roles([99]))

    def test_false_if_one_role_does_not_exit(self):
        self.assertFalse(self.all_roles.has_roles([1, 99]))

    def test_true_for_empty_roles(self):
        self.assertTrue(self.all_roles.has_roles([]))


class TestGetMatchingRolesByName(TestCase):

    def setUp(self):
        self.all_roles = DiscordRoles(ALL_ROLES)

    def test_return_role_if_matches(self):
        role_name = 'alpha'
        expected = ROLE_ALPHA
        result = self.all_roles.role_by_name(role_name)
        self.assertEqual(result, expected)

    def test_return_role_if_matches_and_limit_max_length(self):
        role_name = 'x' * 120
        expected = create_role(77, 'x' * 100)
        roles = DiscordRoles([expected])
        result = roles.role_by_name(role_name)
        self.assertEqual(result, expected)

    def test_return_empty_if_not_matches(self):
        role_name = 'lima'
        expected = {}
        result = self.all_roles.role_by_name(role_name)
        self.assertEqual(result, expected)


class TestUnion(TestCase):

    def test_distinct_sets(self):
        roles_1 = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        roles_2 = DiscordRoles([ROLE_CHARLIE, ROLE_MIKE])
        roles_3 = roles_1.union(roles_2)
        expected = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO, ROLE_CHARLIE, ROLE_MIKE])
        self.assertEqual(roles_3, expected)

    def test_overlapping_sets(self):
        roles_1 = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        roles_2 = DiscordRoles([ROLE_BRAVO, ROLE_MIKE])
        roles_3 = roles_1.union(roles_2)
        expected = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO, ROLE_MIKE])
        self.assertEqual(roles_3, expected)

    def test_identical_sets(self):
        roles_1 = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        roles_2 = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        roles_3 = roles_1.union(roles_2)
        expected = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        self.assertEqual(roles_3, expected)


class TestDifference(TestCase):

    def test_distinct_sets(self):
        roles_1 = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        roles_2 = DiscordRoles([ROLE_CHARLIE, ROLE_MIKE])
        roles_3 = roles_1.difference(roles_2)
        expected = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        self.assertEqual(roles_3, expected)

    def test_overlapping_sets(self):
        roles_1 = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        roles_2 = DiscordRoles([ROLE_BRAVO, ROLE_MIKE])
        roles_3 = roles_1.difference(roles_2)
        expected = DiscordRoles([ROLE_ALPHA])
        self.assertEqual(roles_3, expected)

    def test_identical_sets(self):
        roles_1 = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        roles_2 = DiscordRoles([ROLE_ALPHA, ROLE_BRAVO])
        roles_3 = roles_1.difference(roles_2)
        expected = DiscordRoles([])
        self.assertEqual(roles_3, expected)
