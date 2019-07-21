import os
import sys
import mock
import unittest
import json
import datetime
from mock import patch

from flask import request, jsonify

import authMock
from database import create_session
from mod_config.models import Service
from mod_honeypot.models import Profile, PiModels, PiPotReport, ProfileService, \
    CollectorTypes, Deployment
from tests.testAppBase import TestAppBase


class TestServiceManagement(TestAppBase):

    def setUp(self):
        super(TestServiceManagement, self).setUp()

    def tearDown(self):
        super(TestServiceManagement, self).tearDown()

    @patch('mod_report.forms.DashboardForm.validate_deployment')
    @patch('mod_report.forms.DashboardForm.validate_service')
    @patch('mod_report.forms.DashboardForm.validate_report_type')
    def testDynamicDataReport(self, validate_report_type, validate_service, validate_deployment):
        deployment_id = 1
        service_id = 1
        report_type = 1
        try:
            db = create_session(self.app.config['DATABASE_URI'], drop_tables=False)
            # create service, profile, delpoyment
            service = Service(name='test-service', description="test")
            profile = Profile(name='test-profile', description="test")
            db.add(service)
            db.add(profile)
            db.commit()
            profile_row = db.query(Profile.id).first()
            deployment = Deployment(
                name='test-deloyment', profile_id=profile_row.id,
                instance_key='test', mac_key='test',
                encryption_key='test', rpi_model=PiModels.from_string('one'),
                server_ip='test', interface='test',
                wlan_config='test', hostname='test',
                rootpw='test', debug=True,
                collector_type=CollectorTypes.from_string('tcp'))
            db.add(deployment)
            db.commit()
            # create report data
            current_time = datetime.datetime.now()
            time_before_a_week = current_time - datetime.timedelta(days=8)
            data_num_within_a_week = 20
            data_num_before_a_week = 10
            for i in range(data_num_within_a_week):
                report_data = PiPotReport(deployment_id=1, message="test", timestamp=current_time)
                db.add(report_data)
                db.commit()
            for i in range(data_num_before_a_week):
                report_data = PiPotReport(deployment_id=1, message="test", timestamp=time_before_a_week)
                db.add(report_data)
                db.commit()
            db.remove()
            # request without the number of data specified
            data_num = -1
            with self.app.test_client() as client:
                data = dict(
                    deployment=deployment_id,
                    service=service_id,
                    report_type=report_type,
                    data_num=data_num
                )
                response = client.post('/dashboard/load', data=data, follow_redirects=False)
                self.assertEqual(response.get_json()['status'], 'success')
                self.assertEqual(response.get_json()['data_num'], data_num_within_a_week)
            # request with the number of data specified
            data_num = min(data_num_within_a_week + 10, data_num_before_a_week + data_num_within_a_week)
            with self.app.test_client() as client:
                data = dict(
                    deployment=deployment_id,
                    service=service_id,
                    report_type=report_type,
                    data_num=data_num
                )
                response = client.post('/dashboard/load', data=data, follow_redirects=False)
                self.assertEqual(response.get_json()['status'], 'success')
                self.assertEqual(response.get_json()['data_num'], data_num)
            data_num = data_num_before_a_week + data_num_within_a_week + 10
            with self.app.test_client() as client:
                data = dict(
                    deployment=deployment_id,
                    service=service_id,
                    report_type=report_type,
                    data_num=data_num
                )
                response = client.post('/dashboard/load', data=data, follow_redirects=False)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()['status'], 'success')
                self.assertEqual(response.get_json()['data_num'], data_num_before_a_week + data_num_within_a_week)
        finally:
            db.remove()


if __name__ == '__main__':
    unittest.main()
