import os
import string
import sys

import binascii

import subprocess
from flask import Blueprint, g, send_file, abort, url_for, redirect, \
    jsonify, request, make_response

import netifaces as ni

from Crypto import Random
from sqlalchemy import and_

from decorators import get_menu_entries, template_renderer
from mod_auth.controllers import check_access_rights, login_required
from mod_config.models import Service
from mod_honeypot.forms import NewDeploymentForm, ModifyProfileForm, \
    NewProfileForm, ServiceProfileForm
from mod_honeypot.models import Profile, ProfileService, Deployment, PiPotReport, \
    PiModels, CollectorTypes

mod_honeypot = Blueprint('honeypot', __name__)


@mod_honeypot.before_app_request
def before_request():
    g.menu_entries['honeypot'] = get_menu_entries(
        g.user, 'Honeypot instances', 'rocket', '', [
            {'title': 'Profile mgmt', 'icon': 'bookmark', 'route':
                'honeypot.profiles'},
            {'title': 'Honeypot mgmt', 'icon': 'rocket', 'route':
                'honeypot.manage'}
        ]
    )


@mod_honeypot.route('/profiles', methods=['GET', 'POST'])
@login_required
@check_access_rights()
@template_renderer()
def profiles():
    form = NewProfileForm()
    if form.validate_on_submit():
        profile = Profile(form.name.data, form.description.data)
        g.db.add(profile)
        g.db.commit()
        return redirect(url_for('.profiles_id', id=profile.id))
    return {
        'profiles': Profile.query.order_by(Profile.name.asc()),
        'form': form
    }


@mod_honeypot.route('/profiles/<id>', methods=['GET', 'POST'])
@login_required
@check_access_rights(".profiles")
@template_renderer()
def profiles_id(id):
    profile = Profile.query.filter(Profile.id == id).first()
    if profile is None:
        abort(404)
    form = ModifyProfileForm()
    if form.validate_on_submit():
        if form.type.data == 'delete':
            g.db.delete(profile)
            g.db.commit()
            return redirect(url_for('.profiles'))
        else:
            profile.description = form.description.data
            g.db.commit()
            return redirect(url_for('.profiles_id', id=id))
    service_form = ServiceProfileForm()
    service_form.service_id.choices = [(s.id, s.name) for s in
                                       Service.query.all()]
    if request.is_xhr:
        result = {
            'status': 'error',
            'errors': ['invalid action']
        }
        if service_form.validate_on_submit():
            if service_form.service_type.data == 'add':
                # Check if service already exists for this profile
                ps = ProfileService.query.filter(and_(
                    ProfileService.profile_id == profile.id,
                    ProfileService.service_id == service_form.service_id.data)
                ).first()
                if ps is None:
                    ps = ProfileService(
                        profile.id, service_form.service_id.data,
                        service_form.service_configuration.data
                    )
                    g.db.add(ps)
                    g.db.commit()
                    result['status'] = 'success'
                else:
                    result['errors'] = ['this service is already enabled '
                                        'for this profile']
            elif service_form.service_type.data == 'edit':
                ps = ProfileService.query.filter(and_(
                    ProfileService.profile_id == profile.id,
                    ProfileService.service_id == service_form.service_id.data)
                ).first()
                ps.service_configuration = \
                    service_form.service_configuration.data
                g.db.commit()
                result['status'] = 'success'
            elif service_form.service_type.data == 'delete':
                ps = ProfileService.query.filter(and_(
                    ProfileService.profile_id == profile.id,
                    ProfileService.service_id == service_form.service_id.data)
                ).first()
                g.db.delete(ps)
                g.db.commit()
                result['status'] = 'success'
        else:
            errors = []
            for err in service_form.errors.itervalues():
                errors.extend(err)
            result['errors'] = errors
        return jsonify(result)
    return {
        'profile': profile,
        'form': form,
        'service_form': service_form
    }


@mod_honeypot.route('/manage', methods=['GET', 'POST'])
@login_required
@check_access_rights()
@template_renderer()
def manage():
    from run import app
    new_deploy = NewDeploymentForm()
    new_deploy.rpi_model.choices = [(key, value) for key, value in PiModels]
    new_deploy.profile_id.choices = [
        (p.id, p.name) for p in Profile.query.all()]
    new_deploy.collector_type.choices = [(key, value) for key, value in
                                         CollectorTypes]

    if request.is_xhr:
        result = {
            'status': 'error',
            'errors': ['invalid action']
        }
        if new_deploy.validate_on_submit():
            # Generate random keys
            encryption_key = binascii.hexlify(Random.new().read(16))
            chars = string.ascii_letters + string.digits
            instance_key = ''.join(
                chars[ord(os.urandom(1)) % len(chars)] for i in range(16)
            )
            mac_key = ''.join(
                chars[ord(os.urandom(1)) % len(chars)] for i in range(32)
            )
            deployment = Deployment(
                new_deploy.name.data, new_deploy.profile_id.data,
                instance_key, mac_key, encryption_key,
                PiModels.from_string(new_deploy.rpi_model.data),
                new_deploy.server_ip.data, new_deploy.interface.data,
                new_deploy.wlan_configuration.data, new_deploy.hostname.data,
                new_deploy.rootpw.data, new_deploy.debug.data,
                CollectorTypes.from_string(new_deploy.collector_type.data)
            )
            g.db.add(deployment)
            g.db.commit()
            result['status'] = 'success'
            result['id'] = deployment.id
        else:
            errors = []
            for err in new_deploy.errors.itervalues():
                errors.extend(err)
            result['errors'] = errors
        return jsonify(result)

    if sys.platform.startswith("linux"):
        addrs = ni.ifaddresses(app.config.get('NETWORK_INTERFACE'))
        new_deploy.server_ip.data = addrs[ni.AF_INET][0]['addr']
        print('Setting default ip: %s' % addrs[ni.AF_INET][0]['addr'])
    else:
        print('Windows platform is currently unsupported; interfaces below '
              'for debug purposes')
        print(ni.interfaces())
    return {
        'deployments': Deployment.query.order_by(Deployment.name.asc()),
        'form': new_deploy
    }


@mod_honeypot.route('/manage/<id>/<action>')
@login_required
@check_access_rights(".manage")
def manage_id(id, action):
    from run import app
    result = {
        'status': 'error',
        'errors': ['invalid action']
    }
    deployment = Deployment.query.filter(Deployment.id == id).first()
    if deployment is not None:
        if action == 'download' and deployment.has_image():
            response = make_response()
            response.headers['Content-Description'] = 'File Transfer'
            response.headers['Cache-Control'] = 'no-cache'
            response.headers['Content-Type'] = 'application/octet-stream'
            response.headers['Content-Disposition'] = \
                'attachment; filename=%s' % deployment.get_normalized_name()
            response.headers['Content-Length'] = os.path.getsize(
                deployment.get_image_path())
            response.headers['X-Accel-Redirect'] = \
                '/' + os.path.join('honeypot_images',
                                   deployment.get_normalized_name())

            return response
        elif action == 'generate':
            create_image = os.path.join(
                os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                'bin', 'create_image.sh'
            )
            args = [
                create_image, id,
                deployment.get_normalized_name(),
                deployment.get_json_config_string(
                     app.config['COLLECTOR_UDP_PORT'],
                     app.config['COLLECTOR_SSL_PORT']
                ),
                deployment.hostname, deployment.rootpw,
                "%r" % deployment.debug, deployment.wlan_config
            ]
            if sys.platform.startswith("linux"):
                devnull = open(os.devnull, 'w')
                subprocess.Popen(args, stdout=devnull,
                                 stderr=subprocess.STDOUT)
            else:
                print('Windows unsupported; arguments for debug')
                print(args)
            result['status'] = 'success'
            result['progress'] = 0
            return jsonify(result)
        elif action == 'progress':
            result['status'] = 'success'
            result['progress'] = deployment.get_progress()
            return jsonify(result)
        elif action == 'delete':
            # Delete image
            if deployment.has_image():
                os.remove(deployment.get_image_path())
            # Delete from DB
            g.db.delete(deployment)
            g.db.commit()
            result['status'] = 'success'
            return jsonify(result)
    abort(403)
