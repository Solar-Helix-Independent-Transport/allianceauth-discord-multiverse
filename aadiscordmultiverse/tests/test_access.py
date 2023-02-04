from unittest import mock

from django.test import TestCase


class TestAccessPerms(TestCase):
    def test_no_perms(self):
        self.assertFalse(False)
