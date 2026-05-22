import configparser
from pathlib import Path

from pyramid.config import Configurator
from pyramid.session import SignedCookieSessionFactory

from .config import routes


def _apply_local_ini_overrides(global_config, settings):
    config_path = global_config.get('__file__')
    if not config_path:
        return
    local_path = Path(config_path + '.local')
    if not local_path.exists():
        return

    parser = configparser.RawConfigParser()
    parser.read(str(local_path))
    if not parser.has_section('app:main'):
        return

    for key, value in parser.items('app:main'):
        settings[key] = value

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    _apply_local_ini_overrides(global_config, settings)
    session_secret = settings.get(
        'multitwitch.session_secret',
        'dev-only-session-secret-change-me',
    )
    session_factory = SignedCookieSessionFactory(session_secret)
    config = Configurator(
        settings=settings,
        session_factory=session_factory,
    )
    config.include(routes)
    return config.make_wsgi_app()
