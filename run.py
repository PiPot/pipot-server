import os
import traceback

import sys

from flask import Flask, g
from config_parser import parse_config
from database import create_session
from decorators import template_renderer
from mod_auth.controllers import mod_auth
from mod_config.controllers import mod_config
from mod_honeypot.controllers import mod_honeypot
from mod_report.controllers import mod_report
from mod_support.controllers import mod_support

app = Flask(__name__)
config = parse_config('config')
app.config.from_mapping(config)
try:
    app.config['DEBUG'] = os.environ['DEBUG']
except KeyError:
    app.config['DEBUG'] = False


def install_secret_keys(application, secret_session='secret_key',
                        secret_csrf='secret_csrf'):
    """Configure the SECRET_KEY from a file
    in the instance directory.

    If the file does not exist, print instructions
    to create it from a shell with a random key,
    then exit.

    """
    do_exit = False
    session_file = os.path.join(application.root_path, secret_session)
    csrf_file = os.path.join(application.root_path, secret_csrf)
    try:
        application.config['SECRET_KEY'] = open(session_file, 'rb').read()
    except IOError:
        traceback.print_exc()
        print('Error: No secret key. Create it with:')
        if not os.path.isdir(os.path.dirname(session_file)):
            print('mkdir -p', os.path.dirname(session_file))
        print ('head -c 24 /dev/urandom >', session_file)
        do_exit = True

    try:
        application.config['CSRF_SESSION_KEY'] = open(csrf_file, 'rb').read()
    except IOError:
        print('Error: No secret CSRF key. Create it with:')
        if not os.path.isdir(os.path.dirname(csrf_file)):
            print('mkdir -p', os.path.dirname(csrf_file))
        print('head -c 24 /dev/urandom >', csrf_file)
        do_exit = True

    if do_exit:
        sys.exit(1)


if not app.config['TESTING']:
    install_secret_keys(app)


# Expose submenu method for jinja templates
def sub_menu_open(menu_entries, active_route):
    for menu_entry in menu_entries:
        if 'route' in menu_entry and menu_entry['route'] == active_route:
            return True
    return False

app.jinja_env.globals.update(sub_menu_open=sub_menu_open)


@app.errorhandler(404)
@template_renderer('404.html', 404)
def not_found(error):
    return


@app.errorhandler(500)
@template_renderer('500.html', 500)
def internal_error(error):
    print(error)
    traceback.print_exc()
    return


@app.errorhandler(403)
@template_renderer('403.html', 403)
def forbidden(error):
    return {
        'user_role': g.user.role_id,
        'endpoint': error.description
    }


@app.before_request
def before_request():
    g.server_name = app.config.get('INSTANCE_NAME', '')
    g.menu_entries = {}
    g.db = create_session(app.config['DATABASE_URI'])
    g.version = "0.6"


@app.teardown_appcontext
def teardown(exception):
    db = g.get('db', None)
    if db is not None:
        db.remove()

# Register blueprints
app.register_blueprint(mod_auth, url_prefix='/auth')  # Needs to be first
app.register_blueprint(mod_config)
app.register_blueprint(mod_report)
app.register_blueprint(mod_honeypot)
app.register_blueprint(mod_support)

if __name__ == '__main__':
    # Run in development mode; Werkzeug server
    # Load variables for running (if defined)
    ssl_context = host = None
    proto = 'https'
    key = app.config.get('SSL_KEY', '')
    cert = app.config.get('SSL_CERT', '')
    if len(key) == 0 or len(cert) == 0:
        ssl_context = 'adhoc'
    else:
        ssl_context = (cert, key)

    server_name = app.config.get('SERVER_IP', '0.0.0.0')
    port = app.config.get('SERVER_PORT', 443)

    print('Server should be running soon on ' +
          '{0}://{1}:{2}'.format(proto, server_name, port))
    if server_name != '127.0.0.1':
        host = '0.0.0.0'
    app.run(host, port, app.config['DEBUG'], ssl_context=ssl_context)
