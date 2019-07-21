import datetime
import json
import os
import enum

from sqlalchemy import Column, Integer, String, Text, ForeignKey, orm, Boolean, Enum

from database import Base
from pipot.services.IService import IModel


class Profile(Base):
    __tablename__ = 'profile'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    description = Column(Text)
    services = orm.relationship("ProfileService")

    def __init__(self, name, description):
        self.name = name
        self.description = description

    def __repr__(self):
        return '<Profile %r: %r>' % (self.id, self.name)


class ProfileService(Base):
    __tablename__ = 'profile_service'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    profile_id = Column(
        Integer,
        ForeignKey('profile.id', onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True
    )
    service_id = Column(
        Integer,
        ForeignKey('service.id', onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True
    )
    service_configuration = Column(Text)
    service = orm.relationship("Service")

    def __init__(self, profile_id, service_id, service_configuration):
        self.profile_id = profile_id
        self.service_id = service_id
        self.service_configuration = service_configuration

    def __repr__(self):
        return '<ProfileService %r,%r>' % (self.profile_id, self.service_id)

    def get_service_config(self):
        """
        Parses the extra service config into a dict, or returns an empty one.

        :return: A JSON parsed configuration dict.
        :rtype: dict
        """
        if self.service_configuration is None or len(
                self.service_configuration) == 0:
            return {}
        else:
            return json.loads(self.service_configuration)


class PiModels(enum.Enum):
    one = "one"
    two = "two"
    three = "three"


class CollectorTypes(enum.Enum):
    udp = "udp"
    tcp = "tcp"

class Deployment(Base):
    __tablename__ = 'deployment'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    profile_id = Column(
        Integer,
        ForeignKey('profile.id', onupdate="CASCADE", ondelete="RESTRICT")
    )
    profile = orm.relationship("Profile")
    instance_key = Column(String(20))
    mac_key = Column(String(32))
    encryption_key = Column(String(32))
    rpi_model = Column(Enum(PiModels))
    server_ip = Column(String(46))  # IPv6 proof
    interface = Column(String(20))
    wlan_config = Column(Text())
    hostname = Column(String(64))
    rootpw = Column(String(50))
    debug = Column(Boolean())
    collector_type = Column(Enum(CollectorTypes))

    def __init__(self, name, profile_id, instance_key, mac_key,
                 encryption_key, rpi_model, server_ip, interface,
                 wlan_config, hostname, rootpw, debug, collector_type):
        self.name = name
        self.profile_id = profile_id
        self.instance_key = instance_key
        self.mac_key = mac_key
        self.encryption_key = encryption_key
        self.rpi_model = rpi_model
        self.server_ip = server_ip
        self.interface = interface
        self.wlan_config = wlan_config
        self.hostname = hostname
        self.rootpw = rootpw
        self.debug = debug
        self.collector_type = collector_type

    def get_image_path(self):
        return os.path.join(
            './honeypot_images',
            self.get_normalized_name()
        )

    def get_normalized_name(self):
        return 'deployment_%s_%s.img' % (
                self.id,
                self.name.lower().replace(' ', '_')
            )

    def has_image(self):
        return os.path.isfile(self.get_image_path())

    def get_progress(self):
        progress_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            'bin', '%s_progress.txt' % self.id
        )
        try:
            with open(progress_file) as f:
                progress = f.read().strip("\n")
        except IOError:
            progress = 0

        return int(progress)

    def is_ready(self):
        return self.get_progress() == 100

    def get_json_config_string(self, udp_port, tcp_port):
        return json.dumps({
            "collector": {
                "interface": self.interface,
                "protocol": self.collector_type.value,
                "instance_key": self.instance_key,
                "mac_key": self.mac_key,
                "encryption_key": self.encryption_key,
                "port": udp_port if self.collector_type == CollectorTypes.udp
                else tcp_port,
                "host": self.server_ip
            },
            "services": [
                {'name': ps.service.name, 'config': ps.get_service_config()}
                for ps in self.profile.services]
        })


class PiPotReport(IModel):
    __tablename__ = 'report_pipot'

    message = Column(Text(1000))

    def __init__(self, deployment_id, message, timestamp=None):
        super(PiPotReport, self).__init__(deployment_id, timestamp)
        self.message = message

    def get_message_for_level(self, notification_level):
        pass
