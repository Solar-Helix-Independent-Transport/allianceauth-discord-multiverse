import logging

from django.contrib import admin

from allianceauth.services.admin import ServicesUserAdmin

from .models import DiscordManagedServer, MultiDiscordUser, ServerActiveFilter

logger = logging.getLogger(__name__)

admin.site.register(ServerActiveFilter)

@admin.register(MultiDiscordUser)
class MultiDiscordUserAdmin(ServicesUserAdmin):
    search_fields = ServicesUserAdmin.search_fields + ('uid', 'username')
    list_display = ServicesUserAdmin.list_display + \
        ('activated', '_username', '_uid')
    list_filter = ServicesUserAdmin.list_filter + ('activated',)
    ordering = ('-activated',)

    @admin.display(
        description='Discord ID (UID)',
        ordering='uid',
    )
    def _uid(self, obj):
        return obj.uid


    @admin.display(
        description='Discord Username',
        ordering='username',
    )
    def _username(self, obj):
        if obj.username and obj.discriminator:
            return f'{obj.username}#{obj.discriminator}'
        else:
            return ''

    def delete_queryset(self, request, queryset):
        for user in queryset:
            user.delete_user()



@admin.register(DiscordManagedServer)
class DiscordMultiverseServer(admin.ModelAdmin):
    list_display = ['server_name', 'guild_id', 'sync_names']
    filter_horizontal = [
        "included_groups",
        "faction_access",
        "alliance_access",
        "corporation_access",
        "character_access",
        "group_access",
        "state_access",
        ]
