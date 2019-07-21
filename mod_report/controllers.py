import datetime
from flask import Blueprint, g, jsonify, request, render_template_string

from decorators import template_renderer, get_menu_entries
from mod_auth.controllers import login_required, check_access_rights

# Register blueprint
from mod_honeypot.models import Deployment, PiPotReport
from mod_report.forms import DashboardForm
from pipot.services.ServiceLoader import get_class_instance

mod_report = Blueprint('report', __name__)


@mod_report.before_app_request
def before_request():
    g.menu_entries['report'] = get_menu_entries(
        g.user, 'Dashboard', 'dashboard', 'report.dashboard')


@mod_report.route('/')
@login_required
@check_access_rights()
@template_renderer()
def dashboard():
    # Get active deployments
    deployments = Deployment.query.all()
    data = [
        {
            'id': d.id,
            'name': d.name,
            'profile': d.profile.name,
            'profile_id': d.profile.id,
            'services': [
                {
                    'id': ps.service.id,
                    'name': ps.service.name,
                    'report_types': get_class_instance(
                        ps.service.name, None, None).get_report_types()
                } for ps in d.profile.services
            ]
        } for d in deployments
    ]
    for d in data:
        d['services'].append(
            {
                'id': 0,
                'name': 'General information',
                'report_types': ['General data']
            }
        )
    return {
        'data': data,
        'form': DashboardForm()
    }


@mod_report.route('/dashboard/<action>', methods=['POST'])
@login_required
@check_access_rights('.dashboard')
def dashboard_ajax(action):
    from run import app
    result = {
        'status': 'error',
        'errors': ['invalid action']
    }
    if action == 'load':
        form = DashboardForm(request.form)
        if form.validate_on_submit():
            if form.is_pipot:
                template_string = \
                    '<table><thead><tr><th>ID</th><th>Timestamp</th>' \
                    '<th>Message</th></tr></thead><tbody>' \
                    '{% for entry in entries %}<tr><td>{{ entry.id }}</td>' \
                    '<td>{{ entry.timestamp }}</td><td>{{ entry.message }}' \
                    '</td></tr>{% else %}<tr><td colspan="4">No entries ' \
                    'for this timespan</td></tr>{% endfor %}</tbody></table>'
                if form.data_num.data == -1:
                    timestamp = datetime.datetime.utcnow() - datetime.timedelta(
                        days=7)
                    data = PiPotReport.query.filter(
                        PiPotReport.timestamp >= timestamp).order_by(
                        PiPotReport.timestamp.desc()).all()
                else:
                    data = PiPotReport.query.filter().order_by(
                        PiPotReport.timestamp.desc()).limit(form.data_num.data).all()
                result['data_num'] = len(data)
                template_args = {
                    'entries': data
                }
            else:
                service = get_class_instance(form.service_inst.name, None,
                                             None)
                report_type = form.report_type.data
                template_string = service.get_template_for_type(report_type)
                template_args = service.get_template_arguments(
                    report_type,
                    service.get_data_for_type(
                        report_type,
                        **service.get_data_for_type_default_args(
                            report_type
                        )
                    )
                )
            result['status'] = 'success'
            result['html'] = render_template_string(
                template_string, **template_args)
        else:
            result['errors'] = form.errors
    if action == 'data':
        # TODO: add implementation for more data request from the client
        # side (to allow dynamic reloading of data)
        result['status'] = 'success'
        result['payload'] = ''
    return jsonify(result)
