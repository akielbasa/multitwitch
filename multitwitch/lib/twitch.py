import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


AUTHORIZE_URL = 'https://id.twitch.tv/oauth2/authorize'
TOKEN_URL = 'https://id.twitch.tv/oauth2/token'
VALIDATE_URL = 'https://id.twitch.tv/oauth2/validate'
FOLLOWED_CHANNELS_URL = 'https://api.twitch.tv/helix/channels/followed'
FOLLOWED_STREAMS_URL = 'https://api.twitch.tv/helix/streams/followed'


class TwitchAPIError(Exception):
    def __init__(self, message, status_code=None):
        Exception.__init__(self, message)
        self.status_code = status_code


class TwitchClient(object):
    def __init__(self, settings):
        self.client_id = settings.get('multitwitch.twitch_client_id', '').strip()
        self.client_secret = settings.get('multitwitch.twitch_client_secret', '').strip()
        self.redirect_uri = settings.get('multitwitch.twitch_redirect_uri', '').strip()
        self.scope = settings.get(
            'multitwitch.twitch_scope',
            'user:read:follows',
        ).strip()

    def is_configured(self):
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def create_authorize_url(self, state):
        query = urllib.parse.urlencode({
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': self.scope,
            'state': state,
        })
        return '%s?%s' % (AUTHORIZE_URL, query)

    def generate_state(self):
        return uuid.uuid4().hex

    def exchange_code(self, code):
        return self._post_form(TOKEN_URL, {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
        })

    def refresh_token(self, refresh_token):
        return self._post_form(TOKEN_URL, {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        })

    def validate_token(self, access_token):
        request = urllib.request.Request(
            VALIDATE_URL,
            headers={
                'Authorization': 'OAuth %s' % access_token,
            },
        )
        return self._load_json(request)

    def get_followed_channels(self, access_token, user_id):
        channels = []
        cursor = None
        while True:
            params = {
                'user_id': user_id,
                'first': '100',
            }
            if cursor:
                params['after'] = cursor
            request = urllib.request.Request(
                '%s?%s' % (
                    FOLLOWED_CHANNELS_URL,
                    urllib.parse.urlencode(params),
                ),
                headers=self._helix_headers(access_token),
            )
            payload = self._load_json(request)
            channels.extend(payload.get('data', []))
            cursor = payload.get('pagination', {}).get('cursor')
            if not cursor:
                break
        return channels

    def get_followed_live_streams(self, access_token, user_id):
        streams = []
        cursor = None
        while True:
            params = {
                'user_id': user_id,
                'first': '100',
            }
            if cursor:
                params['after'] = cursor
            request = urllib.request.Request(
                '%s?%s' % (
                    FOLLOWED_STREAMS_URL,
                    urllib.parse.urlencode(params),
                ),
                headers=self._helix_headers(access_token),
            )
            payload = self._load_json(request)
            streams.extend(payload.get('data', []))
            cursor = payload.get('pagination', {}).get('cursor')
            if not cursor:
                break
        return streams

    def build_auth_record(self, token_payload, validation_payload):
        expires_at = int(time.time()) + int(token_payload.get('expires_in', 0))
        scopes = token_payload.get('scope') or validation_payload.get('scopes') or []
        return {
            'access_token': token_payload.get('access_token'),
            'refresh_token': token_payload.get('refresh_token'),
            'expires_at': expires_at,
            'scope': scopes,
        }

    def build_user_record(self, validation_payload):
        return {
            'id': validation_payload.get('user_id'),
            'login': validation_payload.get('login'),
            'name': validation_payload.get('login'),
            'scopes': validation_payload.get('scopes', []),
        }

    def _helix_headers(self, access_token):
        return {
            'Authorization': 'Bearer %s' % access_token,
            'Client-Id': self.client_id,
        }

    def _post_form(self, url, payload):
        body = urllib.parse.urlencode(payload).encode('utf-8')
        request = urllib.request.Request(url, data=body)
        return self._load_json(request)

    def _load_json(self, request):
        try:
            response = urllib.request.urlopen(request)
            try:
                return json.loads(response.read().decode('utf-8'))
            finally:
                response.close()
        except urllib.error.HTTPError as error:
            status_code = getattr(error, 'code', None)
            raw_body = error.read().decode('utf-8')
            try:
                payload = json.loads(raw_body)
                message = payload.get('message') or payload.get('error') or raw_body
            except ValueError:
                message = raw_body or str(error)
            raise TwitchAPIError(message, status_code=status_code)
        except urllib.error.URLError as error:
            raise TwitchAPIError(str(error))
