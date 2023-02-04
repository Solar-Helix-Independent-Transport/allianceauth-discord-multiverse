import logging

from allianceauth.services.views import superuser_test
from django.contrib import messages
from django.contrib.auth.decorators import (login_required,
                                            permission_required,
                                            user_passes_test)
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

from .models import DiscordManagedServer, MultiDiscordUser

logger = logging.getLogger(__name__)

ACCESS_PERM = 'aadiscordmultiverse.access_discord_multiverse'


@login_required
@permission_required(ACCESS_PERM)
def deactivate_discord(request, guild_id):
    logger.debug("deactivate_discordmv called by user %s", request.user)
    try:
        discord_user = MultiDiscordUser.objects.get(
            guild_id=guild_id, user=request.user)
        if discord_user.delete_user(
            is_rate_limited=False, handle_api_exceptions=True
        ):
            logger.info(
                "Successfully deactivated discord for user %s", request.user)
            messages.success(request, _('Deactivated Discord account.'))

    except Exception as e:
        logger.exception(e, exc_info=True)
        logger.error(
            "Unsuccessful attempt to deactivate discord for user %s", request.user
        )
        messages.error(
            request, _(
                'An error occurred while processing your Discord account.')
        )

    return redirect("services:services")


@login_required
@permission_required(ACCESS_PERM)
def reset_discord(request, guild_id):
    logger.debug("reset_discordmv called by user %s", request.user)
    try:
        discord_user = MultiDiscordUser.objects.get(
            guild_id=guild_id, user=request.user)
        if discord_user.delete_user(
            is_rate_limited=False, handle_api_exceptions=True
        ):
            logger.info(
                "Successfully deleted discord user for user %s - "
                "forwarding to discord activation.",
                request.user
            )
            return redirect("dmv:activate", guild_id=guild_id)
    except Exception as e:
        logger.exception(e, exc_info=True)

    logger.error(
        "Unsuccessful attempt to reset discord for user %s", request.user
    )
    messages.error(
        request, _('An error occurred while processing your Discord account.')
    )
    return redirect("services:services")


@login_required
@permission_required(ACCESS_PERM)
def activate_discord(request, guild_id):
    logger.debug("activate_discordmv called by user %s", request.user)
    return redirect(MultiDiscordUser.objects.generate_oauth_redirect_url(guild_id))


@login_required
@permission_required(ACCESS_PERM)
def discord_callback(request):
    logger.debug(
        "Received DiscordMV callback for activation of user %s", request.user
    )
    authorization_code = request.GET.get('code', None)
    state = request.GET.get('state', None)
    if not authorization_code:
        logger.warning(
            "Did not receive OAuth code from callback for user %s", request.user
        )
        success = False
    elif not state:
        logger.warning(
            "Did not receive state %s", request.user
        )
        success = False
    else:  # TODO Checck perms first.
        guild_id = state
        guild = DiscordManagedServer.objects.get(guild_id=guild_id)
        if MultiDiscordUser.objects.add_user(
            user=request.user,
            authorization_code=authorization_code,
            is_rate_limited=False,
            guild=guild
        ):
            logger.info(
                "Successfully activated Discord account for user %s", request.user
            )
            success = True

        else:
            logger.error(
                "Failed to activate Discord account for user %s", request.user
            )
            success = False

    if success:
        messages.success(
            request, _('Your Discord account has been successfully activated.')
        )
    else:
        messages.error(
            request,
            _(
                'An error occurred while trying to activate your Discord account. '
                'Please try again.'
            )
        )

    return redirect("services:services")


@login_required
@user_passes_test(superuser_test)
def discord_add_bot(request):
    return redirect(MultiDiscordUser.objects.generate_bot_add_url())
