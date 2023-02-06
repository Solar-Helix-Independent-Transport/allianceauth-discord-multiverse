from django.apps import AppConfig

from . import __branch__, __version__


class DiscordMultiVerseServiceConfig(AppConfig):
    name = 'aadiscordmultiverse'
    label = 'aadiscordmultiverse'
    verbose_name = 'Discord Multiverse ({__branch__}:{__version__})'

    def ready(self):
        # run on startup to sync services!
        from .auth_hooks import add_del_callback  # NOPEP8
        try:
            add_del_callback()
        except Exception as e:
            pass
        from . import signals  # NOPEP8
