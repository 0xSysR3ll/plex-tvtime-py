"""
This module contains the implementation of a webhook for TVTime integration with Plex.

Author: 0xsysr3ll
Copyright: © 2024 0xsysr3ll. All rights reserved.
License: see the LICENSE file.

"""

import threading
import os
import json
from werkzeug.http import parse_options_header
from werkzeug.exceptions import BadRequest
from flask import Flask, request
from tvtime import TVTime  # pylint: disable=import-error
from utils.config import Config  # pylint: disable=import-error
from utils.logger import setup_logging, logging as log  # pylint: disable=import-error

setup_logging()
config = Config('config/config.yml')
config.load()

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.logger.setLevel(log.ERROR)


class Webhook():  # pylint: disable=too-few-public-methods
    """
    Class representing a webhook for TVTime integration with Plex.
    """

    def __init__(self, plex_user: str, tvtime_username: str, tvtime_password: str): # pylint: disable=too-many-arguments
        self.tvtime = None
        self.user = plex_user
        self.username = tvtime_username
        self.password = tvtime_password

    def run(self):
        """
        Runs the TVTime integration webhook.
        """
        log.info("Starting TVTime integration...")
        Webhook.tvtime = TVTime(
            user=self.user,
            username=self.username,
            password=self.password,
            driver_location='/usr/local/bin/geckodriver',
            browser_location='/usr/bin/firefox-esr'
        )
        Webhook.tvtime.login()
        log.info("TVTime integration started !")
        app.run(host='0.0.0.0', port=5000, debug=False)


class WebhookHandler:
    """
    Class representing a webhook handler for TVTime integration with Plex.
    """

    @staticmethod
    def parse_content_type():
        """
        Parse the content type from the request headers.

        Returns:
            tuple:  A tuple containing the content type (str)
            and the parameters (dict) parsed from the headers.
            If the content type or parameters are invalid, returns (None, None).
        """
        try:
            content_type, pdict = parse_options_header(
                request.headers.get('Content-Type'))
            if not isinstance(content_type, str) or not isinstance(pdict, dict):
                log.error('Invalid content type')
                return None, None
            return content_type, pdict
        except request.exceptions.RequestException as _:
            log.error('Error parsing content type: %s', _)
            return None, None

    @staticmethod
    def parse_form_data(pdict: dict):
        """
        Parse form data from the given dictionary.

        Args:
            pdict (dict): The dictionary containing the form data.

        Returns:
            dict or None:   The parsed form data as a dictionary,
            or None if there was an error parsing the data.
        """
        if 'boundary' in pdict:
            pdict['boundary'] = pdict['boundary'].encode("utf-8")
        try:
            form_data = request.form
            return form_data.to_dict(flat=False)
        except BadRequest as _:
            log.error('Error parsing form data: %s', _)
            return None

    @staticmethod
    def process_payload(post_vars: dict):
        """
        Process the payload from the form data.

        Args:
            post_vars (dict): The dictionary containing the form data.

        Returns:
            dict or None: The decoded JSON payload if successful, None otherwise.
        """
        if 'payload' not in post_vars:
            log.error('Payload not found in form data')
            return None
        payload = post_vars['payload'][0]
        try:
            return json.loads(payload)
        except json.JSONDecodeError as _:
            log.error('Error decoding JSON payload: %s', _)
            return None

    @staticmethod
    def handle_media(webhook_data: dict): # pylint: disable=too-many-return-statements
        """
        Handles the media scrobble event received from the webhook.

        Args:
            webhook_data (dict): The payload data received from the webhook.

        Returns:
            tuple: A tuple containing the response body and status code.
            The response body is an empty string ('') and the status code is 204
            if the event is invalid, or 'OK' and the status code 200
            if the event is valid and processed successfully.
        """
        event = webhook_data.get('event')
        if event != "media.scrobble":
            return '', 204

        metadata = webhook_data.get('Metadata')
        if not metadata:
            log.error('Metadata not found in payload')
            return '', 204

        plex_user = webhook_data.get('Account').get('title')
        if plex_user != Webhook.tvtime.user:
            log.debug('[%s] User does not have any TVtime account configured', plex_user)
            return '', 204

        media_type = metadata.get('librarySectionType')
        if media_type == 'movie':
            media_name = metadata.get('title')
        else:
            media_name = metadata.get('grandparentTitle')
        if not media_name:
            log.error('Media name not found in metadata')
            return '', 204

        guids = metadata.get('Guid')
        if not guids:
            log.error('GUIDs not found in metadata')
            return '', 204

        media_id = [
            int(guid.get('id').split('tvdb://')[-1])
            for guid in guids
            if guid.get('id').startswith('tvdb://')
        ][0]
        log.debug("[%s] Received a scrobble event for the %s : %s",
                plex_user, media_type, media_name)

        if media_type == 'movie':
            movie_uuid = Webhook.tvtime.get_movie_uuid(movie_id=media_id)
            if movie_uuid is not None:
                Webhook.tvtime.watch_movie(movie_uuid=movie_uuid)
        elif media_type == 'show':
            Webhook.tvtime.watch_episode(episode_id=media_id)
        else:
            log.error('Invalid media type')
            return '', 204

        return 'OK', 200

    @staticmethod
    @app.route('/tvtime/plex', methods=['POST'])
    def plex_webhook():
        """
        Handle the Plex webhook for TVTime integration.

        This method is responsible for processing the incoming webhook payload from Plex
        and handling the media data.

        Returns:
            A response indicating the result of handling the webhook data.
        """
        content_type, pdict = WebhookHandler.parse_content_type()
        if content_type is None or content_type != 'multipart/form-data':
            return '', 204

        post_vars = WebhookHandler.parse_form_data(pdict)
        if post_vars is None:
            return '', 204

        webhook_data = WebhookHandler.process_payload(post_vars)
        if webhook_data is None:
            return '', 204

        return WebhookHandler.handle_media(webhook_data)


if __name__ == '__main__':
    USERS = config.get_config_of('users')
    threads = []
    for user, _ in USERS.items():
        username: str = None
        password: str = None
        try:
            username = _['tvtime']['username']
            password = _['tvtime']['password']
        except KeyError as _:
            log.error('Error parsing configuration : %s', _)
            continue
        t = threading.Thread(
            target=Webhook(
                user, username, password
            ).run)
        t.start()
        threads.append(t)
