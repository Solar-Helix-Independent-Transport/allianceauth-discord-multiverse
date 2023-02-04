import logging

from allianceauth.services.admin import ServicesUserAdmin
from django.contrib import admin

from .models import DiscordManagedServer, MultiDiscordUser

logger = logging.getLogger(__name__)


@admin.register(MultiDiscordUser)
class MultiDiscordUserAdmin(ServicesUserAdmin):
    search_fields = ServicesUserAdmin.search_fields + ('uid', 'username')
    list_display = ServicesUserAdmin.list_display + \
        ('activated', '_username', '_uid')
    list_filter = ServicesUserAdmin.list_filter + ('activated',)
    ordering = ('-activated',)

    def _uid(self, obj):
        return obj.uid

    _uid.short_description = 'Discord ID (UID)'
    _uid.admin_order_field = 'uid'

    def _username(self, obj):
        if obj.username and obj.discriminator:
            return f'{obj.username}#{obj.discriminator}'
        else:
            return ''

    def delete_queryset(self, request, queryset):
        for user in queryset:
            user.delete_user()

    _username.short_description = 'Discord Username'
    _username.admin_order_field = 'username'


@admin.register(DiscordManagedServer)
class DiscordMultiverseServer(admin.ModelAdmin):
    list_display = ['server_name', 'guild_id', 'sync_names']
    filter_horizontal = ["ignored_groups", "faction_access", "alliance_access",
                         "corporation_access", "character_access", "group_access", "state_access"]
