import os
import sys
import mock
import unittest
from mock import patch


from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import scoped_session, sessionmaker

# Need to append server root path to ensure we can import the necessary files.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.config
import flask
from flask import g, current_app, session
from collections import namedtuple
from database import create_session, Base
from mod_auth.models import User, Role, Page, PageAccess
from mod_config.models import Service, Notification, Actions, Conditions, Rule
from mod_honeypot.models import Profile, PiModels, PiPotReport, ProfileService, \
    CollectorTypes, Deployment


def generate_keys(keydir):
    secret_csrf_path = os.path.join(keydir, "secret_csrf")
    secret_key_path = os.path.join(keydir, "secret_key")
    if not os.path.exists(secret_csrf_path):
        secret_csrf_cmd = "head -c 24 /dev/urandom > {path}".format(path=secret_csrf_path)
        os.system(secret_csrf_cmd)
    if not os.path.exists(secret_key_path):
        secret_key_cmd = "head -c 24 /dev/urandom > {path}".format(path=secret_key_path)
        os.system(secret_key_cmd)

    return {'secret_csrf_path': secret_csrf_path, 'secret_key_path': secret_key_path}


def load_config(keydir):
    key_paths = generate_keys(keydir)
    with open(key_paths['secret_key_path'], 'rb') as secret_key_file:
        secret_key = secret_key_file.read()
    with open(key_paths['secret_csrf_path'], 'rb') as secret_csrf_file:
        secret_csrf = secret_csrf_file.read()

    return {
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_POOL_SIZE': 1,
            'SECRET_KEY': secret_key,
            'CSRF_SESSION_KEY': secret_csrf,
            'SERVER_IP': '127.0.0.1',
            'SERVER_PORT': 443,
            'INSTANCE_NAME': 'testInstance',
            'APPLICATION_ROOT': '/',
            'CSRF_ENABLED': False,
            'DATABASE_URI': tests.config.DATABASE_URI,
            'COLLECTOR_UDP_PORT': 1234,
            'COLLECTOR_SSL_PORT': 1235
            }


class TestAppBase(unittest.TestCase):
    keydir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys")

    def create_app(self):
        with patch('config_parser.parse_config', return_value=load_config(self.keydir)):
            from run import app
            return app

    def create_admin(self):
        # test if there is admin existed
        name, password, email = "admin", "adminpwd", "admin@email.com"
        db = create_session(self.app.config['DATABASE_URI'], drop_tables=False)
        role = Role(name=name)
        db.add(role)
        db.commit()
        admin_user = User(role_id=role.id, name=name, password=password, email=email)
        db.add(admin_user)
        db.commit()
        db.remove()
        return name, password, email

    def setUp(self):
        if not os.path.exists(self.keydir):
            os.mkdir(self.keydir)
        self.app = self.create_app()
        self.client = self.app.test_client(self)

    def tearDown(self):
        db = create_session(self.app.config['DATABASE_URI'], drop_tables=False)
        db_engine = create_engine(self.app.config['DATABASE_URI'], convert_unicode=True)
        Base.metadata.drop_all(bind=db_engine)
        db.remove()


class TestApp(TestAppBase):

    def setUp(self):
        super(TestApp, self).setUp()

    def tearDown(self):
        super(TestApp, self).tearDown()

    def test_app_is_running(self):
        self.assertFalse(current_app is None)

    def test_app_is_testing(self):
        self.assertTrue(self.app.config['TESTING'])

    def admin_is_created(self):
        db = create_session(self.app.config['DATABASE_URI'], drop_tables=False)
        admin_row = Role.query.filter(Role.is_admin).first()
        admin = User.query.filter(User.role_id == admin_row.id).first()
        db.remove()
        return admin is not None

    def test_create_admin(self):
        self.create_admin()
        self.assertTrue(self.admin_is_created())


if __name__ == '__main__':
    unittest.main()
