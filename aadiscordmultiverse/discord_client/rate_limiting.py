import logging
import time

from django.core.cache import cache
from django.utils.text import slugify

from .exceptions import DiscordRateLimitExhausted

logger = logging.getLogger(__name__)

seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def interval_to_seconds(s):
    return int(s[:-1]) * seconds_per_unit[s[-1]]


class RateLimitBucket:
    PUT_USER = ("PUT guilds/{guild_id}/members/{user_id}", 10, 10)
    DELETE_USER = ("DELETE guilds/{guild_id}/members/{user_id}", 5, 1)

    BUCKET_HASH = False

    def __init__(self, slug: str, limit: int, window: int):
        self.slug = slugify(slug)
        self.limit = limit
        self.window = window

    def get_key(self):
        return self.BUCKET_HASH if self.BUCKET_HASH else self.slug

    @classmethod
    def choices(cls):
        return [(bucket.slug, bucket.slug.replace("_", " ").title()) for bucket in cls]

    def __str__(self):
        return f"Rate Limit: {self.slug} - {self.limit} in {self.window}Seconds"


class RateLimiter:
    bucket_cache = {}

    def __init__(self) -> None:
        pass

    def _slug_to_key(self, slug) -> str:
        return f"dmv:bucket:{slug}"

    def lookup_slug_bucket(self, slug):
        _b = self.bucket_cache.get(
            slugify(slug),
            False
        )
        if not _b:
            _b = RateLimitBucket(slugify(slug), 5, 1)
            self.bucket_cache[slugify(slug)] = _b

        return _b

    def update_slug_bucket(
        self,
        slug: str,
        limit: int,
        window: int,
        hash: str = "",
        current: int = 5,
        timeout: int = 1
    ):
        bucket = self.lookup_slug_bucket(slug)
        bucket.limit = limit
        bucket.window = window
        bucket.BUCKET_HASH = hash
        self.set_bucket(
            slug,
            current,
            timeout
        )
        logger.info(f"RATES: {slug}/{hash}, {current}/{limit} ({timeout}/{window}s)")

    def init_bucket(self, bucket: RateLimitBucket) -> None:
        # Set our bucket up if it doesn't already exist
        cache.set(
            self._slug_to_key(bucket.get_key()),
            bucket.limit,
            timeout=bucket.window,
            nx=True  # Don't re-create if it does exist
        )

    def get_bucket(self, bucket: RateLimitBucket) -> int:
        # get the value from the bucket
        return int(
            cache.get(
                self._slug_to_key(bucket.get_key()),
                1  # When not found return 1
            )
        )

    def get_timeout(self, bucket: RateLimitBucket) -> int:
        current_bucket = self.get_bucket(bucket)
        if current_bucket <= 0:
            timeout = cache.ttl(self._slug_to_key(bucket.slug)) + 1
            msg = (
                f"Rate limit for bucket '{bucket.slug}':'{bucket.BUCKET_HASH}' exceeded: "
                f"{current_bucket}/{bucket.limit} in last {bucket.window}s. "
                f"Wait {timeout}s."
            )
            logger.warning(msg)
            return timeout  # return the time left till reset
        else:
            return 0  # we are good.

    def decr_bucket(self, slug: str, delta: int = 1) -> int:
        # decrease the bucket value by <delta> from the bucket
        bucket = self.lookup_slug_bucket(slug)
        return cache.decr(
            self._slug_to_key(bucket.get_key()),
            delta
        )

    def set_bucket(self, slug: str, new_limit: int = 5, timeout: int = 0) -> int:
        # set the bucket value
        bucket = self.lookup_slug_bucket(slug)
        return cache.set(
            self._slug_to_key(bucket.get_key()),
            int(new_limit),
            timeout=timeout if timeout else bucket.window
        )

    def check_bucket(self, slug: str):
        bucket = self.lookup_slug_bucket(slug)
        self.init_bucket(bucket)
        # get the value
        bucket_val = self.get_bucket(bucket)
        logger.info(f"RATES: {slug} BV: {bucket_val}")
        if bucket_val <= 0:
            timeout = self.get_timeout(bucket)
            logger.info(f"RATES: {slug} TO: {timeout}")
            if timeout > 0:
                raise DiscordRateLimitExhausted(bucket, timeout, bucket=bucket.slug)
            return

    def check_decr_bucket(self, slug: str, raise_on_limit: bool = True):
        try:
            self.check_bucket(slug)
            logger.info(f"RATES: {slug} DC: {self.decr_bucket(slug)}")
        except DiscordRateLimitExhausted as ex:
            if raise_on_limit:
                raise ex
            else:
                time.sleep(ex.reset)


RateLimits = RateLimiter()
