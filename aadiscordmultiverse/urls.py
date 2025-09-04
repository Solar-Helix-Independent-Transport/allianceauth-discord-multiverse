from django.urls import include, path, re_path

from . import views

app_name = 'dmv'

urlpatterns = [
    # Discord Service Control
    re_path(r'deactivate/(?P<guild_id>(\d)*)',
            views.deactivate_discord, name='deactivate'),
    re_path(r'activate/(?P<guild_id>(\d)*)',
            views.activate_discord, name='activate'),
    re_path(r'reset/(?P<guild_id>(\d)*)', views.reset_discord, name='reset'),
    path('callback/', views.discord_callback, name='callback'),
    path('add_bot/', views.discord_add_bot, name='add_bot'),
]
