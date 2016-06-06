from functools import wraps

from flask import Blueprint, g, request, flash, session, redirect, url_for, \
    abort, jsonify

from decorators import template_renderer, get_menu_entries
from mod_auth.forms import LoginForm, AccountForm, CreateUserForm, \
    UserModifyForm, CreateRoleForm, ToggleRoleForm, DeleteRoleForm
from mod_auth.models import Page, PageAccess, Role, User
from sqlalchemy import not_

mod_auth = Blueprint('auth', __name__)


@mod_auth.before_app_request
def before_app_request():
    user_id = session.get('user_id', 0)
    g.user = User.query.filter(User.id == user_id).first()
    g.menu_entries['auth'] = {
        'title': 'Log in' if g.user is None else 'Log out',
        'icon': 'sign-in' if g.user is None else 'sign-out',
        'route': 'auth.login' if g.user is None else 'auth.logout'
    }
    g.menu_entries['account'] = {
        'title': 'Manage account',
        'icon': 'user',
        'route': 'auth.manage'
    }
    g.menu_entries['config'] = get_menu_entries(
        g.user, 'Configuration', 'cog', '', [
            {'title': 'User manager', 'icon': 'users', 'route':
                'auth.users'},
            {'title': 'Access manager', 'icon': 'check', 'route':
                'auth.access'}
        ]
    )


def login_required(f):
    """
    Decorator that redirects to the login page if a user is not logged in.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('auth.login',
                                    next=request.endpoint))
        return f(*args, **kwargs)
    return decorated_function


def check_access_rights(parent_route=None):
    """
    Decorator that checks if a user can access the page.

    :param parent_route: If the name of the route isn't a regular page (
    e.g. for ajax request handling), pass the name of the parent route.
    :type parent_route: str
    """
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
            if g.user.can_access_route(route):
                return f(*args, **kwargs)
            # Return page not allowed
            abort(403, request.endpoint)

        return decorated_function

    return access_decorator


@mod_auth.route('/login', methods=['GET', 'POST'])
@template_renderer()
def login():
    form = LoginForm(request.form)
    redirect_location = request.args.get('next', '')
    if form.validate_on_submit():
        user = User.query.filter_by(name=form.username.data).first()

        if user and user.is_password_valid(form.password.data):
            session['user_id'] = user.id
            if len(redirect_location) == 0:
                return redirect("/")
            else:
                return redirect(url_for(redirect_location))

        flash('Wrong username or password', 'error-message')

    return {
        'next': redirect_location,
        'adminEmail': User.query.filter(
            User.role_id == Role.query.filter(
                Role.name == 'Admin').first().id).first().email,
        'form': form
    }


@mod_auth.route('/logout')
@template_renderer()
def logout():
    # Destroy session variable
    session.pop('user_id', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('auth.login'))


@mod_auth.route('/manage', methods=['GET', 'POST'])
@login_required
@template_renderer()
def manage():
    form = AccountForm(request.form, g.user)
    if not g.user.is_admin():
        form.email.validators = []
    if request.method == 'POST':
        result = {
            'status': 'error',
            'errors': []
        }
        if form.validate_on_submit():
            user = User.query.filter(User.id == g.user.id).first()
            if user.is_admin():
                user.email = form.email.data
            if len(form.new_password.data) >= 10:
                user.password = User.generate_hash(form.new_password.data)
            g.user = user
            g.db.commit()
            result['status'] = 'success'
        result['errors'] = form.errors
        return jsonify(result)

    return {
        'form': form
    }


@mod_auth.route('/users')
@login_required
@check_access_rights()
@template_renderer()
def users():
    form = CreateUserForm(request.form)
    roles = Role.query.order_by(Role.name.asc())
    form.role.choices = [(r.id, r.name) for r in roles]

    return {
        'users': User.query.filter(User.id != g.user.id).order_by(
            User.name.asc()),  # Don't show own user
        'roles': roles,
        'user_role': roles.filter(Role.name == 'User').first(),
        'form': form
    }


@mod_auth.route('/users/<action>', methods=['POST'])
@login_required
@check_access_rights(".users")
def users_ajax(action):
    result = {
        'status': 'error',
        'errors': []
    }
    if action == 'create':
        form = CreateUserForm(request.form)
        form.role.choices = [(r.id, r.name) for r in
                             Role.query.order_by('name')]
        if form.validate_on_submit():
            # Generate random password
            password = User.create_random_password()
            email = None if len(form.email.data) == 0 else form.email.data
            # No errors, so role is valid, email is valid & username
            # doesn't exist yet. Create user
            user = User(form.role.data, form.username.data, email,
                        User.generate_hash(password))
            g.db.add(user)
            g.db.commit()
            result['status'] = 'success'
            result['user'] = {
                'id': user.id,
                'name': user.name,
                'role_id': user.role_id,
                'role_name': user.role.name,
                'email': user.email,
                'password': password
            }
        result['errors'] = form.errors
    if action == 'delete':
        form = UserModifyForm('delete', g.user, request.form)
        if form.validate_on_submit():
            # Delete user
            user = User.query.filter(User.id == form.id.data).first()
            g.db.delete(user)
            g.db.commit()
            result['status'] = 'success'
        result['errors'] = form.errors
    if action == 'change':
        form = UserModifyForm('change', g.user, request.form)
        if form.validate_on_submit():
            # Change role
            user = User.query.filter(User.id == form.id.data).first()
            role = Role.query.filter(Role.id == form.role.data).first()
            user.role = role
            g.db.commit()
            result['status'] = 'success'
            result['role'] = {
                'id': role.id,
                'name': role.name
            }
        result['errors'] = form.errors
    if action == 'reset':
        form = UserModifyForm('reset', g.user, request.form)
        if form.validate_on_submit():
            # Reset password
            user = User.query.filter(User.id == form.id.data).first()
            password = User.create_random_password()
            user.update_password(password)
            g.db.commit()
            result['status'] = 'success'
            result['message'] = 'The password for %s (#%s) was reset to: ' \
                                '<code>%s</code><br />Please copy ' \
                                'this carefully and give it to the user in ' \
                                'question.' % (user.name, user.id, password)
        result['errors'] = form.errors
    return jsonify(result)


@mod_auth.route('/access', methods=['GET', 'POST'])
@login_required
@check_access_rights()
@template_renderer()
def access():
    form = CreateRoleForm()
    if form.validate_on_submit():
        # Create role
        role = Role(form.name.data)
        g.db.add(role)
        g.db.commit()
        redirect(url_for('.access'))
    return {
        'roles': Role.query.filter(
            Role.id != Role.query.filter(Role.is_admin).first().id
        ).order_by(Role.name.asc()),
        'pages': Page.query.filter(not_(Page.is_global)).order_by(
            Page.name.asc()),
        'form': form
    }


@mod_auth.route('/access/<action>', methods=['POST'])
@login_required
@check_access_rights(".access")
def access_ajax(action):
    result = {
        'status': 'error',
        'errors': []
    }
    if action == 'toggle':
        form = ToggleRoleForm(request.form)
        if form.validate_on_submit():
            role = Role.query.filter(Role.id == form.role.data).first()
            page = Page.query.filter(Page.id == form.page.data).first()
            # Update access for role
            if form.status.data:
                # Add
                role.pages.append(page)
                g.db.commit()
            else:
                # Remove
                role.pages.remove(page)
                g.db.commit()
            result['status'] = 'success'
        result['errors'] = form.errors
    if action == 'delete':
        form = DeleteRoleForm(request.form)
        if form.validate_on_submit():
            # Delete role
            role = Role.query.filter(Role.id == form.role.data).first()
            g.db.delete(role)
            g.db.commit()
            result['status'] = 'success'
        result['errors'] = form.errors

    return jsonify(result)
