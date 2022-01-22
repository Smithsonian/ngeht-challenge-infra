import asyncio
# requires: pip install aiohttp
from slack_utils import get_slack_webhook, slack_message, AsyncWebhookClient


async def send_message_via_webhook(slack_webhook: AsyncWebhookClient):
    t = 'Hello, World!'
    await slack_message(t, slack_webhook)


slack_webhook = get_slack_webhook()
# This is the simplest way to run the async method
# but you can go with any ways to run it
asyncio.run(send_message_via_webhook(slack_webhook))
