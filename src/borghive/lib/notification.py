import logging
import requests
from django.conf import settings  # Add this import

LOGGER = logging.getLogger(__name__)


class Pushover():
    """
    pushover notification
    https://pushover.net/
    """
    # pylint: disable=too-few-public-methods

    base_uri = 'https://api.pushover.net'
    port = 443

    def __init__(self, user, token, **kwargs):
        self.user = user
        self.token = token
        self.base_uri = kwargs.pop('base_uri', self.base_uri)
        self.port = kwargs.pop('port', self.port)

    def push(self, message, **kwargs):
        """pushover to the rescue"""
        LOGGER.debug('send pushover notification: user=%s token=%s', self.user, self.token)

        url = f'{self.base_uri}:{self.port}/1/messages.json'

        # parse config
        data = {
            'user': self.user,
            'token': self.token,
            'message': message
        }
        data.update(kwargs)

        r = requests.post(url, data=data)
        # files = {
        # "attachment": ("image.jpg", open("your_image.jpg", "rb"), "image/jpeg")
        # })
        LOGGER.debug(r.text)
        r.raise_for_status()
        return True


class PagerDuty():
    """
    PagerDuty notification
    https://developer.pagerduty.com/docs/events-api-v2/overview/
    """
    # pylint: disable=too-few-public-methods

    endpoint = '/v2/enqueue'

    def __init__(self, integration_key, **kwargs):
        self.integration_key = integration_key
        self.base_uri = kwargs.pop('base_uri', settings.PAGERDUTY_API_URL)  # Use setting as default
        self.endpoint = kwargs.pop('endpoint', self.endpoint)

    def trigger(self, summary, **kwargs):
        """Trigger a PagerDuty alert"""
        LOGGER.debug('send PagerDuty notification: summary=%s', summary)

        url = f'{self.base_uri}{self.endpoint}'

        payload = {
            "routing_key": self.integration_key,
            "event_action": "trigger",
            "payload": {
                "summary": summary,
                "source": "BorgHive",
                "severity": "info"
            }
        }
        payload.update(kwargs)  # Allow custom overrides

        r = requests.post(url, json=payload, timeout=5)
        LOGGER.debug('PagerDuty response: %s', r.text)
        r.raise_for_status()
        return True
