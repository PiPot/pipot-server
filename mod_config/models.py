import json
import os

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, \
    UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base, DeclEnum


class Service(Base):
    __tablename__ = 'service'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    description = Column(Text)

    def __init__(self, name, description):
        self.name = name
        self.description = description

    def __repr__(self):
        return '<Service %r: %r>' % (self.id, self.name)

    def get_file(self, temp_folder=False):
        return os.path.join(
            './pipot/services',
            'temp' if temp_folder else '',
            self.name
        )


class Notification(Base):
    __tablename__ = 'notification'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    description = Column(Text)

    def __init__(self, name, description):
        self.name = name
        self.description = description

    def __repr__(self):
        return '<Notification %r: %r>' % (self.id, self.name)

    def get_file(self, temp_folder=False):
        return os.path.join(
            './pipot/notifications',
            'temp' if temp_folder else '',
            self.name + '.py'
        )


class Actions(DeclEnum):
    drop = "drop", "Drop"
    store = "store", "Store"


class Conditions(DeclEnum):
    st = '<', '<'
    gt = '>', '>'
    eq = '==', '=='
    se = '<=', '<='
    ge = '>=', '>='
    ne = '!=', '!='


class Rule(Base):
    __tablename__ = 'rule'
    __table_args__ = {
        'mysql_engine': 'InnoDB'
    }
    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey('service.id', onupdate="CASCADE",
                                            ondelete="CASCADE"))
    notification_id = Column(Integer,
                             ForeignKey('notification.id',
                                        onupdate="CASCADE",
                                        ondelete="CASCADE"),
                             nullable=True)
    notification_config = Column(Text)
    condition = Column(Conditions.db_type())
    level = Column(Integer)
    action = Column(Actions.db_type())
    UniqueConstraint('service_id', 'notification_id', 'condition')
    service = relationship(Service)
    notification = relationship(Notification)

    def __init__(self, service_id, notification_id, notification_config,
                 condition, level, action):
        self.service_id = service_id
        self.notification_id = notification_id
        self.notification_config = notification_config
        self.condition = condition
        self.level = level
        self.action = action

    def matches(self, compare_level):
        return eval('%s %s %s' % (compare_level, self.condition.value,
                                  self.level))

    @staticmethod
    def is_valid_condition(condition):
        return condition in ['<', '>', '==', '<=', '>=', '!=']

    def get_notification_config(self):
        """
        Parses the extra notification config into a dict, or returns an empty
        one.

        :return: A JSON parsed configuration dict.
        :rtype: dict
        """
        if self.notification_config is None:
            return {}
        else:
            return json.loads(self.notification_config)
