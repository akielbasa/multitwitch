from multitwitch.lib.session import web, ajax
from multitwitch.lib.twitch import TwitchAPIError, TwitchClient
from pyramid.response import FileResponse
from pyramid.httpexceptions import HTTPFound
import urllib.parse


def _twitch_client(request):
    return TwitchClient(request.registry.settings)


def _current_path(request):
    path = request.path_qs or '/'
    if path.startswith('/auth/') or path.startswith('/api/'):
        return '/'
    return path


def _clear_twitch_session(session):
    session.pop('twitch_auth', None)
    session.pop('twitch_user', None)
    session.pop('twitch_oauth_state', None)
    session.pop('twitch_oauth_next', None)


def _load_followed_channels(request):
    client = _twitch_client(request)
    if not client.is_configured():
        return {
            'configured': False,
            'connected': False,
            'channels': [],
        }

    auth = request.session.get('twitch_auth') or {}
    user = request.session.get('twitch_user') or {}
    access_token = auth.get('access_token')
    refresh_token = auth.get('refresh_token')
    user_id = user.get('id')
    if not access_token or not user_id:
        return {
            'configured': True,
            'connected': False,
            'channels': [],
        }

    try:
        validation = client.validate_token(access_token)
    except TwitchAPIError:
        if not refresh_token:
            _clear_twitch_session(request.session)
            return {
                'configured': True,
                'connected': False,
                'channels': [],
            }
        try:
            refreshed_tokens = client.refresh_token(refresh_token)
            validation = client.validate_token(refreshed_tokens['access_token'])
            request.session['twitch_auth'] = client.build_auth_record(
                refreshed_tokens,
                validation,
            )
            request.session['twitch_user'] = client.build_user_record(validation)
            access_token = refreshed_tokens['access_token']
            user_id = validation.get('user_id')
        except TwitchAPIError:
            _clear_twitch_session(request.session)
            return {
                'configured': True,
                'connected': False,
                'channels': [],
            }

    channels = client.get_followed_channels(access_token, user_id)
    live_streams = client.get_followed_live_streams(access_token, user_id)
    live_by_login = {}
    for stream in live_streams:
        live_by_login[stream.get('user_login')] = stream

    normalized_channels = []
    for channel in channels:
        login = channel.get('broadcaster_login')
        live_stream = live_by_login.get(login)
        normalized_channels.append({
            'login': login,
            'name': channel.get('broadcaster_name') or login,
            'followed_at': channel.get('followed_at'),
            'is_live': bool(live_stream),
            'title': live_stream.get('title') if live_stream else '',
            'viewer_count': live_stream.get('viewer_count') if live_stream else 0,
            'game_name': live_stream.get('game_name') if live_stream else '',
        })

    normalized_channels.sort(
        key=lambda item: (
            0 if item['is_live'] else 1,
            item['name'].lower(),
        )
    )
    return {
        'configured': True,
        'connected': True,
        'channels': normalized_channels,
    }

class WebView:
    @web(template="web/home.tmpl")
    def home(request):
        streams = request.matchdict.get('streams') or []
        if isinstance(streams, str):
            streams = [stream for stream in streams.split('/') if stream]
        darkmode = 'darkmode' in request.params
        uniq_streams = []
        for s in streams:
            if s not in uniq_streams:
                uniq_streams.append(s)
        host = request.host.split(':', 1)[0]
        twitch_parent_hosts = [host]
        if '.' in host and not host.startswith('www.'):
            twitch_parent_hosts.append('www.' + host)
        flashes = []
        for level in ['error', 'success', 'info']:
            for message in request.session.pop_flash(queue=level):
                flashes.append({
                    'level': level,
                    'message': message,
                })
        twitch_client = _twitch_client(request)
        current_path = _current_path(request)
        return {'project' : 'multitwitch',
                'streams' : streams,
                'unique_streams' : uniq_streams,
                'nstreams' : len(streams),
                'darkmode' : darkmode,
                'twitch_parent_hosts' : twitch_parent_hosts,
                'twitch_auth_connected' : bool(request.session.get('twitch_user')),
                'twitch_user' : request.session.get('twitch_user'),
                'twitch_configured' : twitch_client.is_configured(),
                'flash_messages' : flashes,
                'twitch_next' : urllib.parse.quote(current_path, safe='/?:=&')}

    @staticmethod
    def favicon(request):
        return FileResponse("multitwitch/static/favicon.ico", content_type="image/x-icon")

    @staticmethod
    def twitch_login(request):
        client = _twitch_client(request)
        if not client.is_configured():
            request.session.flash(
                'Twitch integration is not configured yet.',
                'error',
            )
            return HTTPFound(location=request.route_url('home'))
        state = client.generate_state()
        request.session['twitch_oauth_state'] = state
        request.session['twitch_oauth_next'] = request.params.get('next') or _current_path(request)
        return HTTPFound(location=client.create_authorize_url(state))

    @staticmethod
    def twitch_callback(request):
        destination = request.session.pop('twitch_oauth_next', '/')
        if request.params.get('error'):
            request.session.flash(
                request.params.get('error_description') or 'Twitch authorization failed.',
                'error',
            )
            return HTTPFound(location=destination)
        expected_state = request.session.pop('twitch_oauth_state', None)
        returned_state = request.params.get('state')
        if not expected_state or expected_state != returned_state:
            request.session.flash('Invalid Twitch OAuth state.', 'error')
            return HTTPFound(location=request.route_url('home'))
        code = request.params.get('code')
        if not code:
            request.session.flash('Missing Twitch authorization code.', 'error')
            return HTTPFound(location=request.route_url('home'))
        try:
            client = _twitch_client(request)
            token_payload = client.exchange_code(code)
            validation_payload = client.validate_token(token_payload['access_token'])
        except TwitchAPIError as error:
            request.session.flash('Twitch login failed: %s' % error, 'error')
            return HTTPFound(location=request.route_url('home'))
        request.session['twitch_auth'] = client.build_auth_record(
            token_payload,
            validation_payload,
        )
        request.session['twitch_user'] = client.build_user_record(validation_payload)
        request.session.flash(
            'Connected Twitch account %s.' % validation_payload.get('login'),
            'success',
        )
        return HTTPFound(location=destination)

    @staticmethod
    def twitch_logout(request):
        _clear_twitch_session(request.session)
        request.session.flash('Disconnected Twitch account.', 'success')
        return HTTPFound(location=request.params.get('next') or request.route_url('home'))

    @ajax()
    def followed_channels(request):
        try:
            return _load_followed_channels(request)
        except TwitchAPIError as error:
            return {
                'configured': True,
                'connected': bool(request.session.get('twitch_user')),
                'channels': [],
                'error': str(error),
            }
        except Exception as error:
            return {
                'configured': True,
                'connected': bool(request.session.get('twitch_user')),
                'channels': [],
                'error': 'Unexpected server error: %s' % error,
            }
