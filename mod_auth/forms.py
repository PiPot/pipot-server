from flask_wtf import Form
from wtforms import PasswordField, StringField, SubmitField, SelectField, \
    IntegerField, BooleanField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Email, ValidationError, \
    InputRequired

from mod_auth.models import User, Role, Page


def email_not_in_use(has_user_field=False):
    def _email_not_in_use(form, field):
        user_id = -1 if not has_user_field else form.user.id
        # Check if email is not already in use
        user = User.query.filter(User.email == field.data).first()
        if user is not None and user.id != user_id and len(field.data) > 0:
            raise ValidationError('this address is already in use')
    return _email_not_in_use


def role_id_is_valid(form, field):
    role = Role.query.filter(Role.id == field.data).first()
    if role is None:
        raise ValidationError('role id is invalid')


class LoginForm(Form):
    username = StringField('Username', [DataRequired(
        message='Username is not filled in.')])
    password = PasswordField('Password', [
        DataRequired(message='Password cannot be empty.')])
    submit = SubmitField('Login')


class AccountForm(Form):
    def __init__(self, formdata=None, obj=None, prefix='', *args, **kwargs):
        super(AccountForm, self).__init__(formdata=formdata, obj=obj, prefix=prefix, *args,
                                          **kwargs)
        self.user = obj

    current_password = PasswordField('Current password', [
        DataRequired(message='current password cannot be empty')
    ])
    new_password = PasswordField('New password')
    new_password_repeat = PasswordField('Repeat new password')
    email = EmailField('Email', [
        DataRequired(message='email address is not filled in'),
        Email(message='entered value is not a valid email address'),
        email_not_in_use(True)
    ])

    @staticmethod
    def validate_current_password(form, field):
        if form.user is not None:
            if not form.user.is_password_valid(field.data):
                raise ValidationError('invalid password')
        else:
            raise ValidationError('user instance not passed to form '
                                  'validation')

    @staticmethod
    def validate_new_password(form, field):
        if form.email is not None:
            # Email form is present, so it's optional
            if len(field.data) == 0 and \
                            len(form.new_password_repeat.data) == 0:
                return

        if len(field.data) == 0:
            raise ValidationError('new password cannot be empty')
        if len(field.data) < 10 or len(field.data) > 500:
            raise ValidationError('password needs to be between 10 and 500 '
                                  'characters long')

    @staticmethod
    def validate_new_password_repeat(form, field):
        if form.email is not None:
            # Email form is present, so it's optional
            if len(field.data) == 0 and len(form.new_password.data) == 0:
                return

        if field.data != form.new_password.data:
            raise ValidationError('the password needs to match the new '
                                  'password')


class CreateUserForm(Form):
    username = StringField('Username', [
        DataRequired(message='username cannot be blank')
    ])
    role = SelectField('Role', coerce=int, validators=[
        DataRequired(message='role not selected'),
        role_id_is_valid
    ])
    email = EmailField('Email', [
        email_not_in_use()
    ])

    @staticmethod
    def validate_username(form, field):
        # Check if a user already exists with this name
        user = User.query.filter(User.name == field.data).first()
        if user is not None:
            raise ValidationError('there is already a user with this name')

    @staticmethod
    def validate_email(form, field):
        # Only need to validate if it's an admin
        if Role.query.filter(Role.id == form.role.data).first().is_admin:
            if len(field.data) == 0:
                raise ValidationError('email cannot be emtpy')


class UserModifyForm(Form):
    def __init__(self, type, user, formdata=None, obj=None, prefix='',
                 **kwargs):
        super(UserModifyForm, self).__init__(formdata, obj, prefix, **kwargs)
        self.type = type
        self.user = user

    id = IntegerField('User id', [
        DataRequired(message='User id cannot be empty.')])
    role = IntegerField('Role id')

    @staticmethod
    def validate_id(form, field):
        user = User.query.filter(User.id == field.data).first()
        if user is None:
            raise ValidationError('Unknown user id.')
        if form.user.id == user.id:
            raise ValidationError('You cannot modify your own account.')

    @staticmethod
    def validate_role(form, field):
        if form.type == 'role':
            # Need to validate the value
            role_id_is_valid(form, field)


class CreateRoleForm(Form):
    name = StringField('Role name', [
        DataRequired(message='role name cannot be empty')])
    submit = SubmitField('Create role')

    @staticmethod
    def validate_name(form, field):
        role = Role.query.filter(Role.name == field.data).first()
        if role is not None:
            raise ValidationError('there is already a role with this name')


class ToggleRoleForm(Form):
    role = IntegerField('Role id', [
        DataRequired(message='role id cannot be empty'),
        role_id_is_valid
    ])
    page = IntegerField('Page id', [
        DataRequired(message='page id cannot be empty')])
    status = BooleanField('Status', [
        InputRequired(message='status cannot be empty')
    ])

    @staticmethod
    def validate_page(form, field):
        page = Page.query.filter(Page.id == field.data)
        if page is None:
            raise ValidationError('page id is invalid')


class DeleteRoleForm(Form):
    role = IntegerField('Role id', [
        DataRequired(message='role id cannot be empty'),
        role_id_is_valid
    ])
