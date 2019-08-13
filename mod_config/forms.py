import re
import os
from enum import Enum
from flask_wtf import Form
from wtforms import SubmitField, FileField, TextAreaField, HiddenField, \
    SelectField, StringField, IntegerField
from wtforms.validators import DataRequired, ValidationError

from mod_config.models import Service, Notification


class FileType(Enum):
    PYTHONFILE = 1
    CONTAINER = 2


def is_python_or_container(file_name):
    # Check if it ends on .py
    is_py = re.compile(r"^[^/\\]*.py$").match(file_name)
    is_container = re.compile((r"^[^/\\]*.zip$")).match(file_name)
    if not is_py and not is_container:
        raise ValidationError('Provided file is not a python (.py) file or a container (.zip)!')
    return FileType.CONTAINER if is_container else FileType.PYTHONFILE


def simple_service_file_validation(check_service=False):
    def validate_file(form, field):
        field.data.filename = os.path.basename(field.data.filename)
        file_type = is_python_or_container(field.data.filename)
        if file_type is FileType.PYTHONFILE:
            # Name cannot be one of the files we already have
            if field.data.filename in ['__init__py', 'IService.py',
                                       'ServiceLoader.py']:
                raise ValidationError('Illegal file name!')
            if check_service:
                # Name cannot be registered already
                service = Service.query.filter(Service.name ==
                                               field.data.filename).first()
                if service is not None:
                    raise ValidationError('There is already an interface with '
                                          'this name!')
    return validate_file


def simple_notification_file_validation(check_notification=True):
    def validate_file(form, field):
        file_type = is_python_or_container(field.data.filename)
        if file_type == FileType.PYTHONFILE:
            # Name cannot be one of the files we already have
            if field.data.filename in ['__init__py', 'INotification.py',
                                       'NotificationLoader.py']:
                raise ValidationError('Illegal file name!')
            if check_notification:
                # Name cannot be registered already
                notification = Notification.query.filter(
                    Notification.name == field.data.filename).first()
                if notification is not None:
                    raise ValidationError('There is already an interface with '
                                          'this name!')
    return validate_file


class NewServiceForm(Form):
    file = FileField('Service file', [
        DataRequired(message='No service file was provided.'),
        simple_service_file_validation(check_service=True)
    ])
    description = TextAreaField('Service description', [
        DataRequired(message='Service description cannot be empty.')],
                                render_kw={'rows': 5})
    submit = SubmitField('Upload new service file')


class BaseServiceForm(Form):
    id = HiddenField('Id', [
        DataRequired(message='no id was provided.')
    ])

    @staticmethod
    def validate_id(form, field):
        # Needs to be a valid service
        service = Service.query.filter(Service.id == field.data).first()
        if service is None:
            raise ValidationError('invalid service id')


class EditServiceForm(BaseServiceForm):
    description = TextAreaField('Service description', [
        DataRequired(message='service description cannot be empty.')],
                                render_kw={'rows': 5})


class UpdateServiceForm(BaseServiceForm):
    file = FileField('Service file', [
        DataRequired(message='no service file was provided.'),
        simple_service_file_validation(check_service=False)
    ])


class NewNotificationForm(Form):
    file = FileField('Notification file', [
        DataRequired(message='No notification file was provided.'),
        simple_notification_file_validation()
    ])
    description = TextAreaField('Notification description', [
        DataRequired(message='Notification description cannot be empty.')
    ], render_kw={'rows': 5})
    submit = SubmitField('Upload new notification file')


class BaseNotificationForm(Form):
    id = HiddenField('Id', [
        DataRequired(message='no id was provided.')
    ])

    @staticmethod
    def validate_id(form, field):
        # Needs to be a valid service
        notification = Notification.query.filter(
            Notification.id == field.data).first()
        if notification is None:
            raise ValidationError('invalid service id')


class EditNotificationForm(BaseNotificationForm):
    description = TextAreaField('Notification description', [
        DataRequired(message='notification description cannot be empty.')
    ], render_kw={'rows': 5})


class UpdateNotificationForm(BaseNotificationForm):
    file = FileField('Notification file', [
        DataRequired(message='no notification file was provided.'),
        simple_notification_file_validation(False)
    ])


class RuleForm(Form):
    service_id = SelectField('Service', coerce=int, validators=[
        DataRequired(message='service not selected')
    ])
    condition = SelectField('Condition', coerce=str, validators=[
        DataRequired(message='condition not selected')
    ])
    level = IntegerField('Level', validators=[
        DataRequired(message='level not entered')
    ])
    notification_id = SelectField('Notification', coerce=int, validators=[
        DataRequired(message='notification not selected')
    ])
    notification_config = TextAreaField(
        'Additional notification configuration')
    action = SelectField('Action', coerce=str, validators=[
        DataRequired(message='action not selected')
    ])


class DeleteRuleForm(Form):
    id = HiddenField('Id', [DataRequired(message='no id was provided.')])
