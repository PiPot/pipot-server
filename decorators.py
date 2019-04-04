import copy
from datetime import date
from functools import wraps

from flask import request, g, render_template


def get_permissible_entries(user, entry):
    """
    Function to get permissible sub-entries recursively.

    :param user: The user object.
    :type user: mod_auth.models.User
    :param entry: The sub entry.
    :type entry: dict

    """

    allowed_entry = copy.deepcopy(
        entry)  # entry can be a nested dictionary so deepcopy is used
    allowed_entry[
        'entries'] = []  # emptying the list of allowed entries. Permissible sub entries to be appended to this list and returned.

    if 'entries' not in entry.keys():
        entry['entries'] = []

    if user.can_access_route(entry['route']):
        for each_child in entry['entries']:
            if 'entries' not in each_child.keys():
                each_child['entries'] = []
            permissible_entries = get_permissible_entries(user, each_child)
            if permissible_entries != {}:  # if get_permissible_entries() has not returned a {}, route of this child can be accessed by current user
                allowed_entry['entries'].append(
                    permissible_entries)  # append this child to list of permissible sub-entries
    else:
        return {}  # return an empty dictionary if user can't access route of the current entry.

    if allowed_entry['entries'] == []:  # if there are no permissible child entries,The key 'entries' is removed.
        allowed_entry.pop('entries')

    return allowed_entry


def get_menu_entries(user, title, icon, route='', all_entries=None):
    """
    Parses a given set of entries and checks which ones the user can access.

    :param user: The user object.
    :type user: mod_auth.models.User
    :param title: The title of the root menu entry.
    :type title: str
    :param icon: The icon of the root menu entry.
    :type icon: str
    :param route: The route of the root menu entry.
    :type route: str
    :param all_entries: The sub entries for this menu entry.
    :type all_entries: list[dict]
    :return: A dict consisting of the menu entry.
    :rtype: dict
    """
    if all_entries is None:
        all_entries = []
    result = {
        'title': title,
        'icon': icon
    }
    allowed_entries = []
    passed = False
    if user is not None:
        if len(route) > 0:
            result['route'] = route
            passed = user.can_access_route(route)
        else:
            for entry in all_entries:
                if user.can_access_route(entry['route']):
                    allowed_entries.append(get_permissible_entries(user, entry))
            if len(allowed_entries) > 0:
                result['entries'] = allowed_entries
                passed = True

    return result if passed else {}


def template_renderer(template=None, status=200):
    """
    Decorator to render a template.

    :param template: The template if it's not equal to the name of the
    endpoint.
    :type template: str
    :param status: The return code
    :type status: int
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            template_name = template
            if template_name is None:
                template_name = request.endpoint.replace('.', '/') + '.html'
            ctx = f(*args, **kwargs)

            if ctx is None:
                ctx = {}
            elif not isinstance(ctx, dict):
                return ctx
            # Add default values
            ctx['applicationName'] = 'PiPot (Micro Honeypot for RPi)'
            ctx['applicationNameShort'] = 'PiPot'
            ctx['applicationVersion'] = getattr(g, 'version', 'Unknown')
            ctx['serverName'] = getattr(g, 'server_name', 'Default server')
            ctx['currentYear'] = date.today().strftime('%Y')
            user = getattr(g, 'user', None)
            ctx['user'] = user
            # Create menu entries
            menu_entries = getattr(g, 'menu_entries', {})
            ctx['menu'] = [
                menu_entries.get('report', {}),
                menu_entries.get('config', {}),
                menu_entries.get('honeypot', {}),
                menu_entries.get('support', {}),
                menu_entries.get('account', {}),
                menu_entries.get('auth', {})
            ]
            ctx['active_route'] = request.endpoint

            # Render template & return
            return render_template(template_name, **ctx), status

        return decorated_function

    return decorator
