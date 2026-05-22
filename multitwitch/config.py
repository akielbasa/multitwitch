from multitwitch.views.web import WebView

def routes(config):
    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('favicon', '/favicon.ico')
    config.add_view(WebView.favicon, route_name='favicon')

    config.add_route('home', '/')
    config.add_view(WebView.home, route_name='home')

    config.add_route('auth_twitch_login', '/auth/twitch/login')
    config.add_view(WebView.twitch_login, route_name='auth_twitch_login')

    config.add_route('auth_twitch_callback', '/auth/twitch/callback')
    config.add_view(WebView.twitch_callback, route_name='auth_twitch_callback')

    config.add_route('auth_twitch_logout', '/auth/twitch/logout')
    config.add_view(WebView.twitch_logout, route_name='auth_twitch_logout')

    config.add_route('api_followed_channels', '/api/followed-channels')
    config.add_view(WebView.followed_channels, route_name='api_followed_channels')

    config.add_route('watch', '/*streams')
    config.add_view(WebView.home, route_name='watch')
