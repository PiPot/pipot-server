import json

from flask_wtf import Form
from wtforms import SubmitField, HiddenField, SelectField, StringField, \
    TextAreaField, PasswordField, BooleanField
from wtforms.validators import DataRequired, ValidationError

from mod_honeypot.models import Deployment, Profile


class NewDeploymentForm(Form):
    name = StringField('Deployment name', validators=[
        DataRequired(message='name not entered')
    ])
    profile_id = SelectField('Profile', coerce=int, validators=[
        DataRequired(message='profile not selected')
    ])
    rpi_model = SelectField('RPi model', coerce=str, validators=[
        DataRequired(message='RPi model not selected')
    ])
    server_ip = StringField('IP address of the server', validators=[
        DataRequired(message='ip address not entered')
    ])
    interface = StringField(
        'Communication interface',
        validators=[
            DataRequired(message='interface not entered')
        ],
        default="eth0"
    )
    hostname = StringField('Hostname of the deployment', validators=[
        DataRequired(message='host name not entered')
    ])
    rootpw = PasswordField('Password for root user', validators=[
        DataRequired(message='password for root user not set')
    ])
    debug = BooleanField('Leave SSH open for debug purposes')
    collector_type = SelectField('Connection type to server', validators=[
        DataRequired(message='connection type not selected')
    ], coerce=str)
    wlan_configuration = TextAreaField('WPA Supplicant config')
    submit = SubmitField('Create new deployment')

    @staticmethod
    def validate_name(form, field):
        # Name needs to be unique
        deployment = Deployment.query.filter(Deployment.name ==
                                             field.data).first()
        if deployment is not None:
            raise ValidationError('there is already a deployment with this '
                                  'name')


class BaseDeploymentForm(Form):
    id = HiddenField('Id', [DataRequired(message='no id was provided.')])

    @staticmethod
    def validate_id(form, field):
        # Needs to be a valid deployment
        deployment = Deployment.query.filter(
            Deployment.id == field.data).first()
        if deployment is None:
            raise ValidationError('invalid deployment id')


class NewProfileForm(Form):
    name = StringField('Profile name', validators=[
        DataRequired(message='Name not entered.')
    ])
    description = TextAreaField(
        'Profile description',
        validators=[DataRequired(message='Description not entered.')]
    )
    submit = SubmitField('Create new profile')

    @staticmethod
    def validate_name(form, field):
        # Need to check if there's no profile with this name yet
        profile = Profile.query.filter(Profile.name == field.data).first()
        if profile is not None:
            raise ValidationError('A service with this name already exists.')


class ModifyProfileForm(Form):
    type = HiddenField('Type', [
        DataRequired(message='no type was provided.')
    ])
    description = TextAreaField('Profile description')

    @staticmethod
    def validate_type(form, field):
        if field.data not in ['update', 'delete']:
            raise ValidationError('invalid type.')

    @staticmethod
    def validate_description(form, field):
        if form.type.data == 'update':
            # Cannot be empty
            if field.data == '':
                raise ValidationError('description cannot be empty.')


class ServiceProfileForm(Form):
    service_type = HiddenField('Type')
    service_id = SelectField('Service', coerce=int, validators=[
        DataRequired(message='service not selected')
    ])
    service_configuration = TextAreaField('Additional service configuration')

    @staticmethod
    def validate_service_type(form, field):
        if len(field.data) > 0:
            if field.data not in ['edit', 'add', 'delete']:
                raise ValidationError('unknown type')

    @staticmethod
    def validate_service_configuration(form, field):
        # Needs to be valid JSON if entered
        if len(field.data) > 0:
            try:
                json.loads(field.data)
            except ValueError:
                raise ValidationError('provided config is not valid JSON!')
