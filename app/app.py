import os
import json
import cgi
from flask import Flask, request
from tvtime import TVTime
from utils.config import Config
from utils.logger import setup_logging, logging as log

setup_logging()
config = Config('config/config.yml')
config.load()

TVTIME_CONFIG = config.get_config_of('tvtime')

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.logger.setLevel(log.ERROR)


class Webhook():
    """
    Class representing a webhook for TVTime integration with Plex.
    """

    def __init__(self):
        self.tvtime = None

    def run(self):
        """
        Runs the TVTime integration webhook.
        """
        log.info("Starting TVTime integration")
        Webhook.tvtime = TVTime(
            username=TVTIME_CONFIG['username'],
            password=TVTIME_CONFIG['password'],
            driver_location='/usr/local/bin/geckodriver',
            browser_location='/usr/bin/firefox-esr'
        )
        Webhook.tvtime.login()
        log.info("TVTime integration started")
        app.run(host='0.0.0.0', port=5000, debug=False)

    @staticmethod
    @app.route('/tvtime/plex', methods=['POST'])
    def plex_webhook():
        """
        Handles the Plex webhook for TVTime integration.

        Returns:
            A tuple containing the response and status code.
        """
        try:
            content_type, pdict = cgi.parse_header(
                request.headers.get('Content-Type'))
        except Exception as e:
            log.error('Error parsing content type: %s', e)
            return ('', 204)

        if not isinstance(content_type, str) and not isinstance(pdict, dict):
            log.error('Invalid content type')

        if content_type == 'multipart/form-data':
            pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
            pdict['CONTENT-LENGTH'] = int(
                request.headers.get('Content-Length'))
            try:
                post_vars = cgi.parse_multipart(
                    request.environ['wsgi.input'], pdict)
            except:
                log.error('Error parsing form data')
                return ('', 204)

            if 'payload' in post_vars:
                payload = post_vars['payload'][0]
                try:
                    webhook_data = json.loads(payload)
                except json.JSONDecodeError:
                    log.error('Error decoding JSON payload')
            else:
                log.error('Payload not found in form data')
                return ('', 204)
        else:
            return ('', 204)

        event = webhook_data.get('event')
        if event is None:
            log.error('Event not found in payload')
            return ('', 204)

        if event != "media.scrobble":
            return ('', 204)

        metadata = webhook_data.get('Metadata')
        if metadata is None:
            log.error('Metadata not found in payload')
            return ('', 204)

        media_type = metadata.get('librarySectionType')
        if media_type is None:
            log.error('Media type not found in metadata')
            return ('', 204)

        match media_type:
            case 'movie':
                media_name = metadata.get('title')
            case 'show':
                media_name = metadata.get('grandparentTitle')
            case _:
                log.error('Invalid media type')

        if media_name is None:
            log.error('Media name not found in metadata')
            return ('', 204)

        guids = metadata.get('Guid')
        if guids is None:
            log.error('GUIDs not found in metadata')
            return ('', 204)

        media_id = [int(guid.get('id').split('tvdb://')[-1])
                    for guid in guids if guid.get('id').startswith('tvdb://')][0]

        log.debug(
            "Received a scrobble event for the %s : %s ",
            media_type, media_name
        )
        match media_type:
            case 'movie':
                movie_uuid = Webhook.tvtime.get_movie_uuid(movie_id=media_id)
                if movie_uuid is None:
                    return ('', 204)
                Webhook.tvtime.watch_movie(movie_uuid=movie_uuid)
            case 'show':
                Webhook.tvtime.watch_episode(episode_id=media_id)

        return ('OK', 200)


if __name__ == '__main__':
    webhook = Webhook()
    webhook.run()
