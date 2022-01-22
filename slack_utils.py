import os
import json
import logging


from slack_sdk.webhook.async_client import AsyncWebhookClient


LOGGER = logging.getLogger(__name__)


def get_slack_webhook():
    env = os.getenv('SERVER_SLACK_WEBHOOK')
    if env is not None:
        return env

    slack_secrets_file = '~/.slack_secrets'
    try:
        with open(os.path.expanduser(slack_secrets_file), 'r') as fp:
            secrets = json.load(fp)
    except Exception:
        LOGGER.exception('slack secret json load from ~/.slack_secrets failed')
        return

    try:
        url = secrets['webhooks']['ngeht']['analysis-challenge-bots']
    except Exception:
        LOGGER.exception('slack secret json key not found in ~/.slack_secrets')
        return

    return AsyncWebhookClient(url)


async def slack_message(text, webhook):
    if webhook is None:
        LOGGER.warning('not sending slack message because webhook is not configured: '+text)
        return

    if os.getenv('SLACK_QUIET'):
        print('would have sent to slack:')
        print(text)
        return

    response = await webhook.send(text=text)

    if response.status_code != 200:
        LOGGER.warning('abnormal response status from slack webhook: {}'.format(response.status_code))
    elif response.body != 'ok':
        LOGGER.warning('abnormal response body from slack webhook: '+response.body)
