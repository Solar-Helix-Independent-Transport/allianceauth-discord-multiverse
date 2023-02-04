"""This is script is for concurrency testing the Discord client with a Discord server.

It will run multiple requests against Discord with multiple workers in parallel.
The results can be analysed in a special log file.

This script is design to be run manually as unit test, e.g. by running the following:

python manage.py test
allianceauth.services.modules.discord.discord_client.tests.piloting_concurrency

To make it work please set the below mentioned environment variables for your server.
Since this may cause lots of 429s we'd recommend NOT to use your
alliance Discord server for this.
"""

import os
from random import random
import threading
from time import sleep
from django.test import TestCase

from .. import DiscordClient, DiscordApiBackoff

from ...utils import set_logger_to_file

logger = set_logger_to_file(
    'allianceauth.services.modules.discord.discord_client.client', __file__
)

# Make sure to set these environnement variables for your Discord server and user
DISCORD_GUILD_ID = os.environ['DISCORD_GUILD_ID']
DISCORD_BOT_TOKEN = os.environ['DISCORD_BOT_TOKEN']
DISCORD_USER_ID = os.environ['DISCORD_USER_ID']
NICK = 'Dummy'

# Configure these settings to adjust the load profile
NUMBER_OF_WORKERS = 5
NUMBER_OF_RUNS = 10

# max seconds a worker waits before starting a new run
# set to near 0 for max load preassure
MAX_JITTER_PER_RUN_SECS = 1.0


def worker(num: int):
    """worker function"""
    worker_info = 'worker %d' % num
    logger.info('%s: started', worker_info)
    client = DiscordClient(DISCORD_BOT_TOKEN)
    try:
        runs = 0
        while runs < NUMBER_OF_RUNS:
            run_info = '%s: run %d' % (worker_info, runs + 1)
            my_jitter_secs = random() * MAX_JITTER_PER_RUN_SECS
            logger.info('%s - waiting %s secs', run_info, f'{my_jitter_secs:.3f}')
            sleep(my_jitter_secs)
            logger.info('%s - started', run_info)
            try:
                client.modify_guild_member(
                    DISCORD_GUILD_ID, DISCORD_USER_ID, nick=NICK
                )
                runs += 1
            except DiscordApiBackoff as bo:
                message = '%s - waiting out API backoff for %d ms' % (
                    run_info, bo.retry_after
                )
                logger.info(message)
                print()
                print(message)
                sleep(bo.retry_after / 1000)

    except Exception as ex:
        logger.exception('%s: Processing aborted: %s', worker_info, ex)

    logger.info('%s: finished', worker_info)
    return


class TestMulti(TestCase):

    def test_multi(self):
        logger.info('Starting multi test')
        for num in range(NUMBER_OF_WORKERS):
            x = threading.Thread(target=worker, args=(num + 1,))
            x.start()
