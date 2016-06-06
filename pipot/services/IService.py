import os
import datetime

from abc import ABCMeta, abstractmethod

import sys
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship
from twisted.application import internet
from twisted.internet.protocol import Factory, DatagramProtocol
from twisted.python import filepath

from database import Base

if sys.platform.startswith("linux"):
    from twisted.internet import inotify
    from twisted.internet.inotify import INotifyError, IN_CREATE, IN_MODIFY


class IModel(Base):
    """
    Abstract base model for storing entries in the database containing three
    base fields: id, timestamp and deployment_id (foreign key to the
    Deployment table).
    """
    __abstract__ = True
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime())

    @declared_attr
    def deployment_id(cls):
        return Column(
            Integer,
            ForeignKey(
                'deployment.id', onupdate="CASCADE", ondelete="CASCADE")
        )

    @declared_attr
    def deployment(cls):
        return relationship("Deployment")

    def __init__(self, deployment_id, timestamp=None):
        """
        Inits this instance.
        :param deployment_id: The id of the deployment
        :type deployment_id: int
        :param timestamp: A timestamp
        :type timestamp: datetime.datetime
        """
        if timestamp is None:
            timestamp = datetime.datetime.utcnow()
        self.timestamp = timestamp
        self.deployment_id = deployment_id

    @abstractmethod
    def get_message_for_level(self, notification_level):
        """
        Gets a message for a given notification level. This is for sending
        out notifications.

        :param notification_level: The notification level to generate a
        message for for this value.
        :type notification_level: int
        :return: A formatted message containing the needed data.
        :rtype: str
        """
        pass


class IModelIP(IModel):
    """
    Abstract base class implementation that adds an IP & port over the
    already defined fields.
    """
    __abstract__ = True
    ip = Column(String(46))  # IPv6 proof
    port = Column(Integer)

    def __init__(self, deployment_id, ip, port, timestamp=None):
        """
        Inits this instance.
        :param deployment_id: The id of the deployment
        :type deployment_id: int
        :param ip: The IP address.
        :type ip: str
        :param port: The port.
        :type port: int
        :param timestamp: A timestamp
        :type timestamp: datetime.datetime
        """
        super(IModelIP, self).__init__(deployment_id, timestamp)
        self.ip = ip
        self.port = port


class IService:
    """
    Global shared interface for all services. All services implementing
    this interface MUST have a constructor that takes in just the 2
    arguments (collector, config) that the constructor of this class has.
    """
    __metaclass__ = ABCMeta

    def __init__(self, collector, config):
        """
        Creates a new instance of the service.

        :param collector: The instance of the collector that gathers the
            messages, groups them and sends them to the server instance.
        :type collector: serverCollector.ICollector
        :param config: The configuration for this service
        :type config: dict
        """
        self._collector = collector
        self._config = config

    # region Server side methods
    @abstractmethod
    def get_used_table_names(self):
        """
        Returns a list of all the SQLAlchemy table classes this service wants
        to use.

        :return: A list of all SQLAlchemy table classes
        :rtype: dict{str,class}
        """
        return {}

    @abstractmethod
    def create_storage_row(self, deployment_id, data, timestamp):
        """
        Creates an object for the given data, so it can be stored.

        :param deployment_id: The id of the deployment.
        :type deployment_id: int
        :param data: Additional data to create the row object.
        :type data: dict
        :param timestamp: The timestamp.
        :type timestamp: DateTime
        :return: An instance of an IModel.
        :rtype: IModel
        """
        pass

    @abstractmethod
    def get_notification_level(self, storage_row):
        """
        Determines the notification level for a given entry.

        :param storage_row: The entry to examine.
        :type storage_row: IModel
        :return: A notification level.
        :rtype: int
        """
        pass

    @abstractmethod
    def get_ports_used(self):
        """
        Returns a list of the ports this service needs, including any
        used ports from external programs that this service uses.

        :return: A list of used ports.
        :rtype: list[int]
        """
        return []

    @abstractmethod
    def get_notification_levels(self):
        """
        Returns a list of positive int values which represent how important a
        message is. The higher, the more importance a message has.

        :return: A list with all the possible notification levels.
        :rtype: list[int]
        """
        pass

    @abstractmethod
    def get_report_types(self):
        """
        Gets the list of report types for this service (for the dashboard).

        :return: A list of strings that represent the possible report types
            for this service.
        :rtype: list[str]
        """
        pass

    @abstractmethod
    def get_data_for_type(self, report_type, **kwargs):
        """
        Returns the data for a given report type and optional arguments.

        :param db_conn: The database connection we need to fetch the data
            from.
        :type db_conn: sqlalchemy.orm.Session
        :param report_type: The report type we want data for.
        :type report_type: str
        :param kwargs: Optional arguments for filtering.
        :type kwargs: any
        :return: Dictionary that can be JSONified.
        :rtype: dict
        """
        pass

    @abstractmethod
    def get_template_for_type(self, report_type):
        """
        Gets the template for a certain type.

        :param report_type: The report type we want data for.
        :type report_type: str
        :return: The initial template for a given report type.
        :rtype: str
        """
        pass

    @abstractmethod
    def get_template_arguments(self, report_type, initial_data):
        """
        Gets the arguments for the template for a given type.

        :param report_type: The report type we want data for.
        :type report_type: str
        :param initial_data: The data that will be passed on to the template.
        :type initial_data: any
        :return: The arguments the template needs.
        :rtype: dict
        """
        pass

    @abstractmethod
    def get_data_for_type_default_args(self, report_type):
        """
        Gets the default arguments for the get_data_for_type method.

        :param report_type: The report type we want data for.
        :type report_type: str
        :return: The default arguments for a given report type.
        :rtype: dict
        """
        pass

    # endregion

    # region installation methods
    def get_apt_dependencies(self):
        """
        Gets a list of the dependencies which need to be installed through
        apt-get. No configuration is possible (a.k.a. silent install is
        only possible).

        :return: A list of the dependencies that need to be installed
            through apt-get.
        :rtype: list[str]
        """
        return []

    def get_pip_dependencies(self):
        """
        Gets a list of the dependencies which need to be installed through
        pip. No configuration is possible (a.k.a. silent install is only
        possible).

        :return: A list of the dependencies that need to be installed
            through pip.
        :rtype: list[str]
        """
        return []

    def after_install_hook(self):
        """
        Runs any necessary post-install operations (e.g. modifying config
        files).

        :return: True on success, false on failure
        :rtype: bool
        """
        return True
    # endregion

    def _send_to_collector(self, log_data):
        """
        Queues given log data in the collector.

        :param log_data: The message. Must be JSON serializable.
        :type log_data: dict
        :return: None
        :rtype: None
        """
        self._collector.queue_data(self.__class__.__name__, log_data)


class INetworkService(IService):
    __metaclass__ = ABCMeta

    def __init__(self, collector, config, port):
        """
        Inits the INetworkService.

        :param collector: The instance of the collector that gathers the
            messages, groups them and sends them to the server instance.
        :type collector: serverCollector.ICollector
        :param config: The configuration for this service
        :type config: dict
        :param port: The port to run on.
        :type port: int
        """
        super(INetworkService, self).__init__(collector, config)
        self.port = port

    def get_ports_used(self):
        # Just a single port...
        return [self.port]

    def log(self, log_data, **kwargs):
        """
        Sends a message (or serializable JSON object) to the collector
        instance. Optionally add transport data.

        :param log_data: The message. Must be JSON serializable.
        :type log_data: dict
        :param kwargs: optional arguments, are added to the log_data (if
            transport is set, it will extract the src_host & src_port from it)
        :return: None
        :rtype: None
        """

        transport = {}
        try:
            transport = kwargs.pop('transport')
            peer = transport.getPeer()
            log_data['src_host'] = peer.host
            log_data['src_port'] = peer.port
        except KeyError:
            pass
        except AttributeError:
            log_data['transport'] = transport

        # Append all kwargs
        log_data.update(kwargs)
        self._send_to_collector(log_data)

    def get_service(self):
        """
        Creates an appropriate instance of either the UDP server or the TCP
        server.

        :return: An instance of the twisted.application.internet.TCPServer
            or twisted.application.UDPServer type, depending on what the
            network service needs to provide.
        :rtype: twisted.application.service.IService
        :raise: Exception if the subclass is no implementation of
            either twisted.application.internet.protocol.Factory or
            twisted.internet.protocol.DatagramProtocol.
        """
        if isinstance(self, Factory):
            return internet.TCPServer(self.port, self)
        elif isinstance(self, DatagramProtocol):
            return internet.UDPServer(self.port, self)

        raise Exception('%s is not an instance of Factory or '
                        'DatagramProtocol' % self.__class__.__name__)


class ISystemService(IService):
    __metaclass__ = ABCMeta

    def __init__(self, collector, config):
        """
        Inits the ISystemService.

        :param collector: The instance of the collector that gathers the
            messages, groups them and sends them to the server instance.
        :type collector: serverCollector.ICollector
        :param config: The configuration for this service
        :type config: dict
        """
        super(ISystemService, self).__init__(collector, config)

    @abstractmethod
    def run(self):
        """
        Runs the necessary commands to start this service up (e.g. call
        other processes, create files, ...)

        :return: None
        :rtype: None
        """
        pass

    @abstractmethod
    def stop(self):
        """
        Called when the daemon gets a sigterm. Can be used to clean up/stop
        external processes, ...

        :return: None
        :rtype: None
        """
        pass


class IFileWatchService(ISystemService):
    __metaclass__ = ABCMeta

    """ :type : file"""
    _file_handle = None
    """ :type : twisted.internet.inotify.INotify"""
    _notifier = None

    def __init__(self, collector, config, file_name=None):
        """
        Inits an instance of IFileWatchService.

        :param collector: The instance of the collector that gathers the
            messages, groups them and sends them to the server instance.
        :type collector: serverCollector.ICollector
        :param config: The configuration for this service
        :type config: dict
        :param file_name: The name of the file to watch.
        :type file_name: str
        """
        super(IFileWatchService, self).__init__(collector, config)
        """ :type : str"""
        self._file_name = file_name
        """ :type : str"""
        self._log_dir = os.path.dirname(os.path.realpath(self._file_name))

    def run(self):
        super(IFileWatchService, self).run()
        self._notifier = inotify.INotify()
        self.open_file()

    def open_file(self, start_at_end=True):
        """
        Opens the file for reading and optionally skips to the end.

        :param start_at_end: Start at the end of the file?
        :type start_at_end: bool
        :return: None
        :rtype: None
        """
        # Check if it's already open, and close if it is
        if self._file_handle is not None:
            self._file_handle.close()

        # Try to open and if needed, skip to end
        try:
            self._file_handle = open(self._file_name)
            if start_at_end:
                self._file_handle.seek(0, os.SEEK_END)
        except IOError:
            self._file_handle = None

        # Start watching the FS (again)
        self._notifier.startReading()
        # Remove old references to the file
        try:
            self._notifier.ignore(filepath.FilePath(self._file_name))
        except KeyError:
            pass
        # Re-add the file we're interested in
        try:
            self._notifier.watch(
                filepath.FilePath(self._file_name),
                callbacks=[self.file_changed]
            )
        except INotifyError:
            self._notifier.watch(
                filepath.FilePath(self._log_dir),
                mask=IN_CREATE,
                callbacks=[self.error_dir_changed]
            )

    @abstractmethod
    def process_lines(self, lines=None):
        """
        Processes the changed lines and does something with them.

        :param lines: A list of changed lines from the log.
        :type lines: list[str]
        :return: None
        :rtype: None
        """
        pass

    def read_lines(self):
        """
        Reads the changed lines since the last call.

        :return: None
        :rtype: None
        """
        if self._file_handle is None:
            return

        lines = self._file_handle.read().strip().split('\n')

        self.process_lines(lines)

    def file_changed(self, ignored, file_path, mask):
        """
        Will be called on file change, so process the lines.

        :param ignored: File handle. DO NOT USE (according to twisted docs).
        :type ignored: Any
        :param file_path: The path to the file that changed
        :type file_path: str
        :param mask: The mask of the file
        :type mask: int
        :return: None
        :rtype: None
        """
        if mask != IN_MODIFY:
            self.open_file()

        self.read_lines()

    def error_dir_changed(self, ignored, file_path, mask):
        """
        Will be called on error, but we want just to try again.

        :param ignored: File handle. DO NOT USE (according to twisted docs).
        :type ignored: Any
        :param file_path: The path to the file that changed
        :type file_path: str
        :param mask: The mask of the file
        :type mask: int
        :return: None
        :rtype: None
        """
        try:
            self._notifier.ignore(filepath.FilePath(self._log_dir))
        except KeyError:
            pass

        if mask != IN_MODIFY:
            self.open_file(False)

        self.read_lines()
