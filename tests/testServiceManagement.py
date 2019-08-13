import os
import sys
import mock
import unittest
import json
import codecs
import filecmp
from mock import patch
from functools import wraps
from werkzeug.datastructures import FileStorage

from flask import request, jsonify

import tests.authMock
from database import create_session
from mod_config.models import Service
from tests.testAppBase import TestAppBase
from pipot.services import ServiceModelsManager

test_dir = os.path.dirname(os.path.abspath(__file__))
service_dir = os.path.join(test_dir, '../pipot/services/')
temp_dir = os.path.join(test_dir, 'temp')
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)
ServiceModelsManager.models_storage = os.path.join(temp_dir, 'models.txt')

class TestServiceManagement(TestAppBase):

    def setUp(self):
        super(TestServiceManagement, self).setUp()
        if not os.path.isfile(ServiceModelsManager.models_storage):
            with open(ServiceModelsManager.models_storage, 'w'):
                pass

    def tearDown(self):
        super(TestServiceManagement, self).tearDown()
        os.remove(ServiceModelsManager.models_storage)

    def add_service(self, service_name, service_file_name):
        # upload the service file
        service_file = codecs.open(os.path.join(test_dir, 'testFiles', service_file_name), 'rb')
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
        # check models.txt is updated
        self.assertEqual(['TelnetService.ReportTelnet'], ServiceModelsManager.get_models())
        # check database
        try:
            db = create_session(self.app.config['DATABASE_URI'], drop_tables=False)
            service_row = db.query(Service.id, Service.name).first()
            service_id = service_row.id
            name = service_row.name
        finally:
            db.remove()
        from database import db_engine
        self.assertTrue(db_engine.has_table('report_telnet'))
        self.assertEqual(service_name, name)
        return service_id

    def remove_service(self, service_id, service_name, service_file_name):
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
        # check models.txt is updated
        self.assertEqual([], ServiceModelsManager.get_models())
        # check database
        try:
            db = create_session(self.app.config['DATABASE_URI'], drop_tables=False)
            service_row = db.query(Service.id, Service.name).first()
            result = (service_row is None)
        finally:
            db.remove()
        self.assertTrue(result)
        from database import db_engine
        self.assertFalse(db_engine.has_table('report_telnet'))
        # clean the service module, otherwise table won't be added to Base.metadata in next test
        del sys.modules['pipot.services.' + service_name + '.' + service_name]

    def update_service(self, service_id, service_name, service_file_name):
        service_file = codecs.open(os.path.join(test_dir, 'testFiles', service_file_name), 'rb')
        # update service file
        with self.app.test_client() as client:
            data = dict(
                serviceUpdate_id=service_id,
                serviceUpdate_file=service_file,
            )
            response = client.post('/services/update', data=data, follow_redirects=False)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()['status'], 'success')
        # check backup service file is removed under temp_path
        self.assertFalse(os.path.isfile(os.path.join(service_dir, 'temp', service_file_name)))
        # check service file and folder still exist under final path
        self.assertTrue(os.path.isdir(os.path.join(service_dir, service_name)))
        self.assertTrue(os.path.isfile(os.path.join(service_dir, service_name, service_name + '.py')))

    def test_add_and_delete_service_file(self):
        service_name = 'TelnetService'
        service_file_name = service_name + '.py'
        service_id = self.add_service(service_name, service_file_name)
        self.remove_service(service_id, service_name, service_file_name)

    def test_add_and_delete_service_container(self):
        service_name = 'TelnetService'
        service_file_name = service_name + '.zip'
        service_id = self.add_service(service_name, service_file_name)
        self.remove_service(service_id, service_name, service_file_name)

    def test_update_with_valid_service_file(self):
        service_name = 'TelnetService'
        service_file_name = service_name + '.py'
        # add a new discription column
        modified_service_file_namae = 'ModifiedService/TelnetService.py'
        service_id = self.add_service(service_name, service_file_name)
        self.update_service(service_id, service_name, modified_service_file_namae)
        # check on metadata
        from database import Base
        has_table = False
        for table in Base.metadata.sorted_tables:
            if table.name == 'report_telnet':
                has_table = True
                self.assertTrue('description' in table.columns.keys())
                break
        self.assertTrue(has_table)
        self.remove_service(service_id, service_name, service_file_name)


if __name__ == '__main__':
    unittest.main()
