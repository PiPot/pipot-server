import os
import sys
import mock
import unittest
import json
from mock import patch
from functools import wraps
from werkzeug.datastructures import FileStorage

from flask import request, jsonify
# Need to append server root path to ensure we can import the necessary files.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import create_session
import mod_auth.controllers
from mod_config.models import Service
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

from tests.testAppBase import TestAppBase

test_dir = os.path.dirname(os.path.abspath(__file__))
service_dir = os.path.join(test_dir, '../pipot/services/')


class TestServiceManagement(TestAppBase):

    def setUp(self):
        super(TestServiceManagement, self).setUp()

    def tearDown(self):
        super(TestServiceManagement, self).tearDown()

    def add_and_remove_service(self, service_name, service_file_name):
        # upload the service file
        # service_name = 'TelnetService'
        # service_file_name = service_name + '.py'
        service_file = open(os.path.join(test_dir, 'testFiles', service_file_name), 'r')
        # service_file = FileStorage(service_file)
        with self.app.test_client() as client:
            data = dict(
                file=service_file,
                description='test'
            )
            response = client.post('/services', data=data, follow_redirects=False)
            self.assertEqual(response.status_code, 200)
        # check service file and folder is created under final_path
        self.assertTrue(os.path.isdir(os.path.join(service_dir, service_name)))
        self.assertTrue(os.path.isfile(os.path.join(service_dir, service_name, service_name + '.py')))
        # check service file and folder is removed under temp_path
        self.assertFalse(os.path.isdir(os.path.join(service_dir, 'temp', service_name)))
        # check database
        db = create_session(self.app.config['DATABASE_URI'], drop_tables=False)
        service_row = db.query(Service.id, Service.name).first()
        service_id = service_row.id
        name = service_row.name
        db.remove()
        self.assertEqual(service_name, name)
        # delete service file
        with self.app.test_client() as client:
            data = dict(
                id=service_id
            )
            response = client.post('/services/delete', data=data, follow_redirects=False)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()['status'], 'success')
        # check service file and folder is removed unser final_path
        self.assertFalse(os.path.isfile(os.path.join(service_dir, service_name, service_file_name)))
        # check database
        db = create_session(self.app.config['DATABASE_URI'], drop_tables=False)
        service_row = db.query(Service.id, Service.name).first()
        result = (service_row is None)
        db.remove()
        self.assertTrue(result)

    def test_add_and_delete_service_file(self):
        service_name = 'TelnetService'
        service_file_name = service_name + '.py'
        self.add_and_remove_service(service_name, service_file_name)

    def test_add_and_delete_service_container(self):
        service_name = 'TelnetService'
        service_file_name = service_name + '.zip'
        self.add_and_remove_service(service_name, service_file_name)


if __name__ == '__main__':
    unittest.main()
