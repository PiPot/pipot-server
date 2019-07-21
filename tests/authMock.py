import os
import sys
from functools import wraps

from flask import request
# Need to append server root path to ensure we can import the necessary files.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mod_auth.controllers
import decorators


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function


def check_access_rights(parent_route=None):
    def access_decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            route = parent_route
            if route is None:
                route = request.endpoint
            elif route.startswith("."):
                # Relative to current blueprint, so we'll need to adjust
                route = request.endpoint[:request.endpoint.rindex('.')] + \
                        route
            return f(*args, **kwargs)
            # Return page not allowed
            abort(403, request.endpoint)
        return decorated_function
    return access_decorator


mod_auth.controllers.login_required = login_required
mod_auth.controllers.check_access_rights = check_access_rights
