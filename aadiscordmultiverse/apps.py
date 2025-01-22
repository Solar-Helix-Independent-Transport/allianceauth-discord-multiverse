import logging

from django.apps import AppConfig

from . import __branch__, __version__

logger = logging.getLogger(__name__)


class DiscordMultiVerseServiceConfig(AppConfig):
    name = 'aadiscordmultiverse'
    label = 'aadiscordmultiverse'
    verbose_name = f"Discord Multiverse ({__branch__}:{__version__})"

    def ready(self):
        # run on startup to sync services!
        from .auth_hooks import add_del_callback  # NOPEP8
        try:
            add_del_callback()
        except Exception as e:
            logger.error("DMV: Failed to Init DMV Server Hook")
            logger.error(e, stack_info=True)

        from . import signals  # NOPEP8
