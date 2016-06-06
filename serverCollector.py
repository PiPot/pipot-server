import hashlib
import hmac
import json

import datetime
from abc import ABCMeta, abstractmethod

from twisted.internet import protocol

from mod_config.models import Rule, Actions
from mod_honeypot.models import PiPotReport, Deployment
from pipot.encryption import Encryption
from pipot.notifications import NotificationLoader
from pipot.services import ServiceLoader


class ICollector:
    """
    Interface that represents a uniform collector.
    """
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def process_data(self, data):
        """
        Server-side processing of received data.

        :param data: A JSONified version of the data.
        :type data: str
        :return: None
        :rtype: None
        """
        pass

    @abstractmethod
    def queue_data(self, service_name, data):
        """
        Client-side processing of data to send

        :param service_name: The name of the service.
        :type service_name: str
        :param data: A JSON collection of data
        :type data: dict
        :return: None
        :rtype: None
        """
        pass


class ServerCollector(ICollector):
    def __init__(self, db):
        super(ServerCollector, self).__init__()
        self.db = db

    def queue_data(self, service_name, data):
        pass

    def process_data(self, data):
        print("Received a message: %s" % data)
        # Attempt to deserialize the data
        try:
            data = json.loads(data)
        except ValueError:
            print('Message not valid JSON; discarding')
            return
        # Check if JSON contains the two required fields
        if 'data' not in data or 'instance' not in data:
            print('Invalid JSON (information missing; discarding)')
            return
        """:type : mod_honeypot.models.Deployment"""
        honeypot = Deployment.query.filter(
            Deployment.instance_key == data['instance']).first()
        if honeypot is not None:
            # Attempt to decrypt content
            decrypted = Encryption.decrypt(honeypot.encryption_key,
                                           data['data'])
            try:
                decrypted_data = json.loads(decrypted)
            except ValueError:
                print('Decrypted data is not JSON; discarding')
                return
            if 'hmac' not in decrypted_data or \
                    'content' not in decrypted_data:
                print('Decrypted data misses info; discarding')
                return
            # Verify message authenticity
            mac = hmac.new(
                str(honeypot.mac_key),
                str(json.dumps(decrypted_data['content'], sort_keys=True)),
                hashlib.sha256
            ).hexdigest()
            try:
                authentic = hmac.compare_digest(
                    mac, decrypted_data['hmac'].encode('utf8'))
            except AttributeError:
                # Older python version? Fallback which is less safe
                authentic = mac == decrypted_data['hmac']

            if authentic:
                print('Data authenticated; processing')
                # Determine service
                for entry in decrypted_data['content']:
                    # Entry exists out of timestamp, service & data elements
                    timestamp = datetime.datetime.utcnow()
                    try:
                        timestamp = datetime.datetime.strptime(
                            entry['timestamp'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        pass
                    if entry['service'] == 'PiPot':
                        # Store
                        row = PiPotReport(honeypot.id, entry['data'],
                                          timestamp)
                        self.db.add(row)
                        self.db.commit()
                        print('Stored PiPot entry in the database')
                    else:
                        # Get active services through the deployment profile
                        for p_service in honeypot.profile.services:
                            if p_service.service.name != entry['service']:
                                continue
                            print('Valid service for profile: %s' %
                                  entry['service'])
                            # Valid service
                            service = ServiceLoader.get_class_instance(
                                entry['service'], self,
                                p_service.get_service_config()
                            )
                            # Convert JSON back to object
                            service_data = service.create_storage_row(
                                honeypot.id, entry['data'], timestamp)
                            notification_level = \
                                service.get_notification_level(service_data)
                            # Get rules that apply here
                            rules = Rule.query.filter(
                                Rule.service_id ==
                                p_service.service_id
                            ).order_by(Rule.level.asc())
                            rule_parsed = False
                            for rule in rules:
                                if not rule.matches(notification_level):
                                    continue
                                # Process message according to rule
                                notifier = \
                                    NotificationLoader.get_class_instance(
                                        rule.notification.name,
                                        rule.get_notification_config()
                                    )
                                notifier.process(
                                    service_data.get_message_for_level(
                                        notification_level
                                    )
                                )
                                if rule.action == Actions.drop:
                                    rule_parsed = True
                                    break
                            if not rule_parsed:
                                # Store in DB
                                self.db.add(service_data)
                                self.db.commit()
                                print('Processed message; stored in DB')
                            else:
                                print('Processed message; dropping due to '
                                      'rules')
                        if len(honeypot.profile.services) == 0:
                            print('There are no services configured for '
                                  'this honeypot; discarding')
            else:
                print('Message not authentic; discarding')
                # print('Expected: %s, got %s' % (mac, decrypted_data[
                # 'hmac']))
                # print('Payload: %s' % json.dumps(decrypted_data['content']))
        else:
            print('Unknown honeypot instance (%s); discarding' %
                  data['instance'])


class SSLCollector(protocol.Protocol):
    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        pass

    def connectionLost(self, reason=protocol.connectionDone):
        pass

    def dataReceived(self, data):
        if 'collector' in self.factory.__dict__:
            self.factory.collector.process_data(data)
        else:
            print('No collector present!')


class SSLFactory(protocol.Factory):
    def __init__(self, collector):
        self.collector = collector

    def buildProtocol(self, addr):
        return SSLCollector(self)


class UDPCollector(protocol.DatagramProtocol):
    def __init__(self, collector):
        self.collector = collector

    def datagramReceived(self, data, addr):
        self.collector.process_data(data)
