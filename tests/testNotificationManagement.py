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
from mod_config.models import Notification
from tests.testAppBase import TestAppBase

test_dir = os.path.dirname(os.path.abspath(__file__))
notification_dir = os.path.join(test_dir, '../pipot/notifications/')
temp_dir = os.path.join(test_dir, 'temp')
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)


def _install_notification_service(cls, update=True, description=""):
    from mod_config.controllers import g
    if not update:
        instance = cls(getattr(cls, 'get_extra_config_sample')())
        notification = Notification(
            instance.__class__.__name__, description)
        g.db.add(notification)
        g.db.commit()
    return True


class TestNotificationManagement(TestAppBase):

    def setUp(self):
        super(TestNotificationManagement, self).setUp()

    def tearDown(self):
        super(TestNotificationManagement, self).tearDown()

    @patch("mod_config.controllers._install_notification_service", side_effect=_install_notification_service)
    def add_notification(self, notification_name, notification_file_name, install_mock):
        # upload the notification file
        notification_file = codecs.open(os.path.join(test_dir, 'testFiles', notification_name,
                                                     notification_file_name), 'rb')
        # notification_file = FileStorage(notification_file)
        with self.app.test_client() as client:
            data = dict(
                file=notification_file,
                description='test'
            )
            response = client.post('/notifications', data=data, follow_redirects=False)
            self.assertEqual(response.status_code, 200)
        install_mock.assert_called_once()
        # check backup notification file is removed under temp_path
        self.assertFalse(os.path.isfile(os.path.join(notification_dir, 'temp', notification_file_name)))
        # check notification file and folder is created under final_path
        self.assertTrue(os.path.isfile(os.path.join(notification_dir, notification_name + '.py')))
        # check database
        try:
            db = create_session(self.app.config['DATABASE_URI'], drop_tables=False)
            notification_row = db.query(Notification.id, Notification.name).first()
            notification_id = notification_row.id
            name = notification_row.name
        finally:
            db.remove()
        self.assertEqual(notification_name, name)
        return notification_id

    def remove_notification(self, notification_id, notification_name):
        # delete notification file
        with self.app.test_client() as client:
            data = dict(
                id=notification_id
            )
            response = client.post('/notifications/delete', data=data, follow_redirects=False)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()['status'], 'success')
        # check notification file and folder is removed unser final_path
        self.assertFalse(os.path.isfile(os.path.join(notification_dir, notification_name + '.py')))
        # check database
        try:
            db = create_session(self.app.config['DATABASE_URI'], drop_tables=False)
            notification_row = db.query(Notification.id).first()
            result = (notification_row is None)
        finally:
            db.remove()
        self.assertTrue(result)

    @patch("mod_config.controllers._install_notification_service", side_effect=_install_notification_service)
    def update_notification(self, notification_id, notification_name, notification_file_name, install_mock):
        notification_file = codecs.open(os.path.join(test_dir, 'testFiles', notification_file_name), 'rb')
        # update notification file
        with self.app.test_client() as client:
            data = dict(
                notificationUpdate_id=notification_id,
                notificationUpdate_file=notification_file,
            )
            response = client.post('/notifications/update', data=data, follow_redirects=False)
            self.assertEqual(response.status_code, 200)
        install_mock.assert_called_once()
        # check backup notification file is removed under temp_path
        self.assertFalse(os.path.isfile(os.path.join(notification_dir, 'temp', notification_name + '.py')))
        # check notification file and folder still exist under final path
        self.assertTrue(os.path.isfile(os.path.join(notification_dir, notification_name + '.py')))
        return response

    def test_add_and_delete_notification_file(self):
        notification_name = 'TelegramNotification'
        notification_file_name = notification_name + '.py'
        notification_id = self.add_notification(notification_name, notification_file_name)
        self.remove_notification(notification_id, notification_name)

    def test_update_with_valid_notification_file(self):
        notification_name = 'TelegramNotification'
        notification_file_name = notification_name + '.py'
        # add a new discription column
        modified_notification_file_namae = 'ModifiedTelegramNotification/TelegramNotification.py'
        notification_id = self.add_notification(notification_name, notification_file_name)
        response = self.update_notification(notification_id, notification_name, modified_notification_file_namae)
        self.assertEqual(response.get_json()['status'], 'success')
        # check file content
        self.assertTrue(filecmp.cmp(os.path.join(notification_dir, notification_file_name),
                                    os.path.join(test_dir, 'testFiles', modified_notification_file_namae)))
        # check on database
        try:
            db = create_session(self.app.config['DATABASE_URI'], drop_tables=False)
            notification_row = db.query(Notification.id, Notification.name).first()
            notification_id = notification_row.id
            name = notification_row.name
        finally:
            db.remove()
        self.assertEqual(notification_name, name)
        self.remove_notification(notification_id, notification_name)

    # def test_update_with_invalid_notification_file(self):
    #     notification_name = 'TelnetService'
    #     notification_file_name = notification_name + '.py'
    #     # try to update an invalid notification file
    #     modified_notification_file_name = 'EmptyTelnetService/TelnetService.py'
    #     notification_id = self.add_notification(notification_name, notification_file_name)
    #     response = self.update_notification(notification_id, notification_name, modified_notification_file_name)
    #     # check the notification file doesn't change
    #     self.assertTrue(filecmp.cmp(os.path.join(notification_dir, notification_name, notification_name + '.py'),
    #                     os.path.join(test_dir, 'testFiles', notification_file_name)))
    #     self.assertEqual(response.get_json()['status'], 'error')
    #     self.remove_notification(notification_id, notification_name)


if __name__ == '__main__':
    unittest.main()
