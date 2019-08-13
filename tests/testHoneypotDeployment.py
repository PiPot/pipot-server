import os
import sys
import mock
import unittest
import json
import datetime
from mock import patch

from flask import request, jsonify

import tests.authMock
from database import create_session
from mod_config.models import Service
from mod_honeypot.models import Profile, PiModels, PiPotReport, ProfileService, \
    CollectorTypes, Deployment
from tests.testAppBase import TestAppBase


class TestHoneypotDeployment(TestAppBase):

    def setUp(self):
        super(TestHoneypotDeployment, self).setUp()

    def tearDown(self):
        super(TestHoneypotDeployment, self).tearDown()

    def test_honeypot_deployment(self):
        # create service, profile, delpoyment
        try:
            db = create_session(self.app.config['DATABASE_URI'], drop_tables=False)
            profile = Profile(name='test-profile', description="test")
            db.add(profile)
            db.commit()
            profile_id = profile.id
        finally:
            db.remove()
        name = 'test_delpoyment'
        with self.app.test_client() as client:
            data = dict(
                profile_id=profile_id,
                name='test_delpoyment',
                rpi_model='one',
                server_ip='127.0.0.1',
                interface='eth0',
                debug=True,
                hostname='admin',
                rootpw='123',
                collector_type='tcp',
                wlan_configuration=''
            )
            response = client.post('manage', data=data, follow_redirects=False, 
                headers=[('X-Requested-With', 'XMLHttpRequest')])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()['status'], 'success')
        # check the deloyment is created is the database
        try:
            db = create_session(self.app.config['DATABASE_URI'], drop_tables=False)
            deloyment_instance = db.query(Deployment.name).first()
            delpoyment_name = deloyment_instance.name
        finally:
            db.remove()
        self.assertEqual(delpoyment_name, name)


if __name__ == '__main__':
    unittest.main()
