from flask_wtf import Form
from flask_wtf.form import _Auto
from wtforms import StringField, IntegerField
from wtforms.validators import DataRequired, ValidationError

from mod_honeypot.models import Deployment
from pipot.services.ServiceLoader import get_class_instance


class DashboardForm(Form):
    deployment = IntegerField('Deployment', validators=[
        DataRequired(message='deployment not selected')
    ])
    service = IntegerField('Service')
    report_type = StringField('Report type', validators=[
        DataRequired(message='report type not selected')
    ])
    data_num = IntegerField('Number of data')

    def __init__(self, formdata=_Auto, obj=None, prefix='', csrf_context=None,
                 secret_key=None, csrf_enabled=None, *args, **kwargs):
        super(DashboardForm, self).__init__(formdata=formdata, obj=obj, prefix=prefix,
                                            csrf_context=csrf_context, secret_key=secret_key,
                                            csrf_enabled=csrf_enabled, *args, **kwargs)
        self.is_pipot = True
        self.service_inst = None

    @staticmethod
    def validate_deployment(form, field):
        # Needs to be a valid deployment
        deployment = Deployment.query.filter(
            Deployment.id == field.data).first()
        if deployment is None:
            raise ValidationError('invalid deployment id')
        form.deployment_inst = deployment

    @staticmethod
    def validate_service(form, field):
        if not form.deployment_inst:
            raise ValidationError('invalid deployment id')
        if field.data == 0:
            return
        # Needs to be a valid service
        services = [ps.service for ps in
                    form.deployment_inst.profile.services]
        service = filter(lambda x: x.id == field.data, services)[0]
        if service is None:
            raise ValidationError('invalid service id')
        form.service_inst = service
        form.is_pipot = False

    @staticmethod
    def validate_report_type(form, field):
        if field.data == 'General data' and form.is_pipot:
            return
        if not form.service_inst:
            raise ValidationError('invalid service id')
        # Needs to be a valid report type
        valid_types = get_class_instance(
            form.service_inst.name, None, None).get_report_types()
        if field.data not in valid_types:
            raise ValidationError('invalid report type')
