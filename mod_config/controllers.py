import os
import sys

import subprocess
import threading
import shutil
import zipfile
import importlib

from flask import Blueprint, g, request, send_file, jsonify, abort, \
    url_for, redirect
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine

from database import create_session
from decorators import get_menu_entries, template_renderer
from mod_auth.controllers import login_required, check_access_rights
from mod_config.forms import NewServiceForm, BaseServiceForm, \
    UpdateServiceForm, EditServiceForm, UpdateNotificationForm, \
    NewNotificationForm, EditNotificationForm, BaseNotificationForm, \
    RuleForm, DeleteRuleForm
from mod_config.models import Service, Notification, Rule, Actions, Conditions
from pipot.notifications import NotificationLoader
from pipot.services import ServiceLoader, ServiceModelsManager

mod_config = Blueprint('config', __name__)


@mod_config.before_app_request
def before_request():
    entries = get_menu_entries(
        g.user, 'Configuration', 'cog', '', [
            {'title': 'Notif. services', 'icon': 'bell-o', 'route':
                'config.notifications'},
            {'title': 'Data processing', 'icon': 'exchange', 'route':
                'config.data_processing'},
            {'title': 'Honeypot services', 'icon': 'sliders', 'route':
                'config.services'}
        ]
    )
    if 'config' in g.menu_entries and 'entries' in entries:
        g.menu_entries['config']['entries'] = entries['entries'] + \
            g.menu_entries['config']['entries']
    else:
        g.menu_entries['config'] = entries


def _install_notification_service_thread(cls, update, description):
    """
        Installs the necessary dependencies for the notification services

        :param cls: The instance of the notification service.
        :type cls: class
        :return: void
        :rtype: void
        """
    from run import app
    apt_deps = getattr(cls, 'get_apt_dependencies')()
    if len(apt_deps) > 0:
        apt = ['apt-get', '-q', '-y', 'install']
        apt.extend(apt_deps)
        print('Calling %s' % " ".join(apt))
        # Call apt-get install
        _ph = subprocess.Popen(apt)
        _ph.wait()

    pip_deps = getattr(cls, 'get_pip_dependencies')()
    if len(pip_deps) > 0:
        pip = ['pip', 'install']
        pip.extend(pip_deps)
        print('Calling %s' % " ".join(pip))
        _ph = subprocess.Popen(pip)
        _ph.wait()

    getattr(cls, 'after_install_hook')()
    if not update:
        instance = cls(getattr(cls, 'get_extra_config_sample')())
        notification = Notification(
            instance.__class__.__name__, description)
        db = create_session(app.config['DATABASE_URI'])
        db.add(notification)
        db.commit()
        db.close()


def _install_notification_service(cls, update=True, description=""):
    """
    Installs the necessary dependencies for the notification services

    :param cls: The class of the notification service.
    :type cls: class
    :return: void
    :rtype: void
    """
    apt_deps = getattr(cls, 'get_apt_dependencies')()
    pip_deps = getattr(cls, 'get_pip_dependencies')()
    if len(apt_deps) > 0 or len(pip_deps) > 0:
        # Need to install dependencies
        t = threading.Thread(
            name='install_notification_service',
            target=_install_notification_service_thread,
            args=(cls, update, description)
        )
        t.start()
        return False
    elif not update:
        instance = cls(getattr(cls, 'get_extra_config_sample')())
        notification = Notification(
            instance.__class__.__name__, description)
        g.db.add(notification)
        g.db.commit()
    return True


@mod_config.route('/notifications', methods=['GET', 'POST'])
@login_required
@check_access_rights()
@template_renderer()
def notifications():
    form = NewNotificationForm()

    if form.validate_on_submit():
        # Process uploaded file
        notification_file = request.files[form.file.name]
        if notification_file:
            filename = secure_filename(notification_file.filename)
            temp_path = os.path.join('./pipot/notifications/temp', filename)
            final_path = os.path.join('./pipot/notifications', filename)
            if not os.path.isfile(final_path):
                notification_file.save(temp_path)
                # Import and verify module
                try:
                    cls = NotificationLoader.load_from_file(temp_path)
                    # Move
                    os.rename(temp_path, final_path)
                    # Reset form
                    description = form.description.data
                    form = NewNotificationForm(None)

                    # Install requirements
                    if not _install_notification_service(
                            cls, False, description):
                        # Delayed insert, show message for delay
                        form.errors['file'] = [
                            'The file was submitted, but dependencies need '
                            'to be installed. It will be listed after refreshing the page if'
                            'said dependencies are installed.'
                        ]
                except NotificationLoader.NotificationLoaderException as e:
                    # Remove file
                    # os.remove(temp_path)
                    # Pass error to user
                    form.errors['file'] = [e.value]
            else:
                form.errors['file'] = ['Service already exists.']
    return {
        'notifications': Notification.query.all(),
        'form': form,
        'updateform': UpdateNotificationForm(prefix='notificationUpdate_')
    }


@mod_config.route('/notifications/<action>', methods=['POST'])
@login_required
@check_access_rights(".notifications")
def notifications_ajax(action):
    result = {
        'status': 'error',
        'errors': ['invalid action']
    }
    if action == 'delete':
        form = BaseNotificationForm(request.form)
        if form.validate_on_submit():
            notification = Notification.query.filter(
                Notification.id == form.id.data).first()
            # Delete service
            g.db.delete(notification)
            # Delete file
            try:
                os.remove(notification.get_file())
                # Finalize service delete
                g.db.commit()
                result['status'] = 'success'
            except EnvironmentError as e:
                g.db.rollback()
                result['errors'] = ['Error during deleting the '
                                    'file %s: %s' % (notification.get_file(),
                                                     e.strerror)]
        else:
            result['errors'] = form.errors
    if action == 'change':
        form = EditNotificationForm(request.form)
        if form.validate_on_submit():
            notification = Notification.query.filter(
                Notification.id == form.id.data).first()
            notification.description = form.description.data
            g.db.commit()
            result['status'] = 'success'
            result['description'] = notification.description
        else:
            result['errors'] = form.errors
    if action == 'update':
        form = UpdateNotificationForm(prefix='notificationUpdate_')
        if form.validate_on_submit():
            notification = Notification.query.filter(
                Notification.id == form.id.data).first()
            notification_file = request.files[form.file.name]
            if notification_file and \
                    notification_file.filename == notification.name + '.py':
                # Save file to temp location
                temp_path = notification.get_file(True)
                notification_file.save(temp_path)
                # Import and verify module
                try:
                    cls = NotificationLoader.load_from_file(temp_path)
                    # Overwrite existing
                    shutil.move(temp_path, notification.get_file())
                    # Update requirements
                    _install_notification_service(cls)
                    result['status'] = 'success'
                    form = UpdateNotificationForm()
                except ServiceLoader.ServiceLoaderException as e:
                    # Remove file
                    os.remove(temp_path)
                    # Pass error to user
                    form.errors['file'] = [e.value]
            else:
                form.errors['file'] = [
                    'Filename does not match the service name'
                ]
        result['errors'] = form.errors
    return jsonify(result)


@mod_config.route('/data-processing', methods=['GET', 'POST'])
@login_required
@check_access_rights()
@template_renderer()
def data_processing():
    form = RuleForm(request.form)
    form.action.choices = [(item.name, item.value) for item in Actions]
    form.condition.choices = [(item.name, item.value) for item in Conditions]
    notification_services = [(n.id, n.name) for n in Notification.query.all()]
    form.notification_id.choices = notification_services
    form.service_id.choices = [(s.id, s.name) for s in Service.query.all()]
    if form.validate_on_submit():
        # Add entry
        rule = Rule(
            form.service_id.data, form.notification_id.data,
            form.notification_config.data,
            Conditions[form.condition.data],
            form.level.data,
            Actions[form.action.data]
        )
        g.db.add(rule)
        g.db.commit()
        return redirect(url_for('.data_processing'))
    return {
        'form': form,
        'rules': Rule.query.all()
    }


@mod_config.route('/data-processing/<action>', methods=['POST'])
@login_required
@check_access_rights(".data_processing")
def data_processing_ajax(action):
    result = {
        'status': 'error',
        'errors': ['invalid action']
    }
    if action == 'delete':
        form = DeleteRuleForm(request.form)
        if form.validate_on_submit():
            rule = Rule.query.filter(Rule.id == form.id.data).first()
            if rule is not None:
                # Delete rule
                g.db.delete(rule)
                g.db.commit()
                result['status'] = 'success'
        else:
            result['errors'] = form.errors
    return jsonify(result)


def verify_and_import_module(final_path, form, is_container=False, re_load=True):
    if is_container:
        instance = ServiceLoader.load_from_container(final_path, temp_folder=False, re_load=re_load)
    else:
        instance = ServiceLoader.load_from_file(final_path, temp_folder=False, re_load=re_load)
    # Auto-generate tables
    instance.get_used_table_names()
    # Update database
    service = Service(instance.__class__.__name__, form.description.data)
    g.db.add(service)
    g.db.commit()
    return instance


@mod_config.route('/services', methods=['GET', 'POST'])
@login_required
@check_access_rights()
@template_renderer()
def services():
    form = NewServiceForm()
    if form.validate_on_submit():
        # Process uploaded file
        file = request.files[form.file.name]
        if file:
            filename = secure_filename(file.filename)
            basename, extname = os.path.splitext(filename)
            final_dir = os.path.join('./pipot/services', basename)
            if not os.path.isdir(final_dir):
                if extname == '.zip':
                    zip_file = zipfile.ZipFile(file)
                    ret = zip_file.testzip()
                    if ret:
                        form.errors['container'] = ['Corrupt container']
                    else:
                        zip_file.extractall('./pipot/services')
                        try:
                            verify_and_import_module(final_dir, form, is_container=True, re_load=False)
                            # Reset form, all ok
                            form = NewServiceForm(None)
                        except ServiceLoader.ServiceLoaderException as e:
                            shutil.rmtree(final_dir)
                            form.errors['container'] = [e.value]
                else:
                    os.mkdir(final_dir)
                    final_file = os.path.join(final_dir, filename)
                    # create the __init__.py for module import
                    file.save(final_file)
                    open(os.path.join(final_dir, '__init__.py'), 'w')
                    # Import and verify module
                    try:
                        verify_and_import_module(final_dir, form, is_container=False, re_load=False)
                        # Reset form, all ok
                        form = NewServiceForm(None)
                    except ServiceLoader.ServiceLoaderException as e:
                        try:
                            del sys.modules['pipot.services.' + basename]
                            del sys.modules['pipot.services.' + basename + '.' + basename]
                        except KeyError:
                            pass
                        # Remove file
                        shutil.rmtree(final_dir)
                        # Pass error to user
                        form.errors['file'] = [e.value]
                # add service name to services.txt
                ServiceModelsManager.add_models(basename)
            else:
                form.errors['file'] = ['Service already exists.']
    return {
        'services': Service.query.all(),
        'form': form,
        'updateform': UpdateServiceForm(prefix='serviceUpdate_')
    }


@mod_config.route('/services/<action>', methods=['POST'])
@login_required
@check_access_rights(".services")
def services_ajax(action):
    result = {
        'status': 'error',
        'errors': ['invalid action']
    }
    if action == 'delete':
        form = BaseServiceForm(request.form)
        if form.validate_on_submit():
            service = Service.query.filter(
                Service.id == form.id.data).first()
            # Delete service in db
            g.db.delete(service)
            # Delete service model
            removed_models = ServiceModelsManager.rm_models(service.name)
            for model_name in removed_models:
                module = importlib.import_module('pipot.services' + '.' + service.name + '.' + service.name)
                model = getattr(module, model_name.lstrip('.' + service.name))
                from database import Base, db_engine
                Base.metadata.drop_all(bind=db_engine, tables=[model.__table__])
                Base.metadata.remove(model.__table__)
            # Delete file
            try:
                shutil.rmtree(service.get_file())
                # Finalize service delete
                g.db.commit()
                result['status'] = 'success'
            except EnvironmentError as e:
                g.db.rollback()
                result['errors'] = ['Error during deleting the '
                                    'file %s: %s' % (service.get_file(),
                                                     e.strerror)]
        else:
            result['errors'] = form.errors
    if action == 'change':
        form = EditServiceForm(request.form)
        if form.validate_on_submit():
            service = Service.query.filter(Service.id == form.id.data).first()
            service.description = form.description.data
            g.db.commit()
            result['status'] = 'success'
            result['description'] = service.description
        else:
            result['errors'] = form.errors
    if action == 'update':
        form = UpdateServiceForm(prefix='serviceUpdate_')
        if form.validate_on_submit():
            # TODO: add support for container-based service update
            service = Service.query.filter(
                Service.id == form.id.data).first()
            file = request.files[form.file.name]
            filename = secure_filename(file.filename)
            basename, extname = os.path.splitext(filename)
            final_dir = os.path.join('./pipot/services', basename)
            temp_dir = os.path.join('./pipot/services', 'temp')
            if file.filename == service.name + '.py':
                # get the original class instance, remove tables from db and meta
                old_instance = ServiceLoader.load_from_file(final_dir, temp_folder=False, re_load=False)
                from database import Base, db_engine
                for table_name, model in old_instance.get_used_table_names().items():
                    Base.metadata.drop_all(bind=db_engine, tables=[model.__table__])
                    Base.metadata.remove(model.__table__)
                # move the original service to temp for backup
                shutil.move(os.path.join(final_dir),
                            os.path.join(temp_dir))
                os.makedirs(final_dir)
                open(os.path.join(final_dir, '__init__.py'), 'w')
                file.save(os.path.join(final_dir, filename))
                # Import and verify module
                try:
                    new_instance = ServiceLoader.load_from_file(final_dir, temp_folder=False, re_load=True)
                    # Reset form, all ok
                    form = NewServiceForm(None)
                    # remove the old service file
                    shutil.rmtree(os.path.join(temp_dir, basename))
                    result['status'] = 'success'
                except ServiceLoader.ServiceLoaderException as e:
                    # bring back the old service file
                    shutil.rmtree(final_dir)
                    shutil.move(os.path.join(temp_dir, basename),
                                os.path.join('./pipot/services'))
                    old_instance = ServiceLoader.load_from_file(final_dir, temp_folder=False, re_load=True)
                    # Pass error to user
                    form.errors['file'] = [e.value]
                    result['errors'] = form.errors
            else:
                form.errors['file'] = [
                    'Filename does not match the service name'
                ]
                result['errors'] = form.errors
        else:
            result['errors'] = form.errors
    return jsonify(result)


@mod_config.route('/services/getInterface/<file>')
@login_required
@check_access_rights(".services")
def get_interface_file(file):
    if file == 'IService':
        return send_file('./pipot/services/IService.py', as_attachment=True)
    elif file == 'INotification':
        return send_file('./pipot/notifications/INotification.py',
                         as_attachment=True)
    else:
        abort(403)
