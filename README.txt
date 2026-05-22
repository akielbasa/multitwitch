Multitwtich -- Multiple twitch streams on one page.

The code of this project is free to use.

Contact me at brian.c.hamrick AT gmail.com

Configuration
-------------

Keep public-safe placeholders in development.ini and production.ini.
Put real local values in an ignored development.ini.local or
production.ini.local file.

Local development
-----------------

Create development.ini.local:

[app:main]
multitwitch.session_secret = change-me
multitwitch.twitch_client_id = change-me
multitwitch.twitch_client_secret = change-me
multitwitch.twitch_redirect_uri = http://localhost:6543/auth/twitch/callback
multitwitch.twitch_scope = user:read:follows

Start the app:

   source .venv/bin/activate
   pserve development.ini

The app automatically loads development.ini.local overrides.
