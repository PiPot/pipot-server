import datetime
from sqlalchemy import Column, String
from twisted.internet.protocol import Protocol, Factory

from pipot.services.IService import INetworkService, IModelIP


class ReportTelnet(IModelIP):
    __tablename__ = 'report_telnet'

    password = Column(String(100))
    description = Column(String(100))  # add for sql-migration test

    def __init__(self, description, deployment_id, ip, port, password, timestamp=None):
        super(ReportTelnet, self).__init__(description, deployment_id, ip, port, timestamp)
        self.description = description
        self.password = password

    def get_message_for_level(self, notification_level):
        message = 'Telnet login attempt with password %s' % self.password
        message += '\nPlease take action!' if notification_level == 2 else ''
        return message


class SimpleTelnetProtocol(Protocol):
    """
    Example Telnet Protocol
    $ telnet localhost 8025
    Trying 127.0.0.1...
    Connected to localhost.
    Escape character is '^]'.
    password:
    password:
    password:
    % Bad passwords
    Connection closed by foreign host.
    """
    def __init__(self):
        self.prompts = 0
        self.buffer = ""

    def connectionMade(self):
        self.transport.write("\xff\xfb\x03\xff\xfb\x01password: ")
        self.prompts += 1

    def dataReceived(self, data):
        """
        Received data is unbuffered so we buffer it for telnet.
        """
        self.buffer += data

        i = self.buffer.find("\x01")
        if i >= 0:
            self.buffer = self.buffer[i+1:]
            return

        if self.buffer.find("\x00") >= 0:
            password = self.buffer.strip("\r\n\x00")
            log_data = {"password": password}
            self.factory.log(log_data, transport=self.transport)
            self.buffer = ""

            if self.prompts < 3:
                self.transport.write("\r\npassword: ")
                self.prompts += 1
            else:
                self.transport.write("\r\n% Bad passwords\r\n")
                self.transport.loseConnection()


class TelnetService(INetworkService, Factory):
    protocol = SimpleTelnetProtocol

    def __init__(self, collector, config):
        super(TelnetService, self).__init__(collector, config, 8025)
        """:type : list"""
        self._report_types = ['entries']

    def get_notification_levels(self):
        return [1, 2]

    def get_used_table_names(self):
        return {ReportTelnet.__tablename__: ReportTelnet}

    def create_storage_row(self, deployment_id, data, timestamp):
        return ReportTelnet(deployment_id, data['src_host'], data['src_port'],
                            data['password'], timestamp)

    def get_notification_level(self, storage_row):
        return 1 if storage_row.password == "admin" else 2

    def get_report_types(self):
        return self._report_types

    def get_data_for_type(self, report_type, **kwargs):
        if report_type == 'entries':
            days = kwargs.pop('time', 7)
            timestamp = datetime.datetime.utcnow() - datetime.timedelta(
                days=days)
            data = ReportTelnet.query.filter(
                ReportTelnet.timestamp >= timestamp).order_by(
                ReportTelnet.timestamp.desc()).all()
            return data
        return {}

    def get_data_for_type_default_args(self, report_type):
        if report_type == 'entries':
            return {'time': 7}
        return {}

    def get_template_for_type(self, report_type):
        if report_type == 'entries':
            return '<table><thead><tr><th>ID</th><th>Timestamp</th>' \
                   '<th>IP:port</th><th>Password</th></tr></thead><tbody>' \
                   '{% for entry in entries %}<tr><td>{{ entry.id }}</td>' \
                   '<td>{{ entry.timestamp }}</td><td>{{ entry.ip}}:' \
                   '{{ entry.port }}</td><td>{{ entry.password }}</td></tr>' \
                   '{% else %}<tr><td colspan="4">No entries for this ' \
                   'timespan</td></tr>{% endfor %}</tbody></table>'
        return ''

    def get_template_arguments(self, report_type, initial_data):
        if report_type == 'entries':
            return {
                'entries': initial_data
            }
        return {}
