from unittest import TestCase

from ..exceptions import (
    DiscordApiBackoff,
    DiscordClientException,
    DiscordRateLimitExhausted,
    DiscordTooManyRequestsError
)


class TestExceptions(TestCase):

    def test_DiscordApiException(self):
        with self.assertRaises(DiscordClientException):
            raise DiscordClientException()

    def test_DiscordApiBackoff_raise(self):
        with self.assertRaises(DiscordApiBackoff):
            raise DiscordApiBackoff(999)

    def test_DiscordApiBackoff_retry_after_seconds(self):
        retry_after = 999
        ex = DiscordApiBackoff(retry_after)
        self.assertEqual(ex.retry_after, retry_after)
        self.assertEqual(ex.retry_after_seconds, 1)

    def test_DiscordRateLimitedExhausted_raise(self):
        with self.assertRaises(DiscordRateLimitExhausted):
            raise DiscordRateLimitExhausted(999)

    def test_DiscordApiBackoffError_raise(self):
        with self.assertRaises(DiscordTooManyRequestsError):
            raise DiscordTooManyRequestsError(999)
