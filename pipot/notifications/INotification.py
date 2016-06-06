from abc import ABCMeta, abstractmethod


class INotification:
    """
    Class that represents the interface for a Notification service.
    """

    __metaclass__ = ABCMeta

    def __init__(self, config):
        """
        Initializes this notification service.

        :param config: A dictionary containing the extra configuration
        :type config: dict
        """
        if self.is_valid_extra_config(config):
            self.config = config
        else:
            raise ValueError("Invalid configuration passsed")

    @abstractmethod
    def process(self, message):
        """
        Sends out the given message.

        :param message: The message to send out
        :type message: str
        :return: void
        :rtype: void
        """
        pass

    @abstractmethod
    def requires_extra_config(self):
        """
        Indicates if this notification service expects extra config or not.

        :return: True if extra configuration is needed, False otherwise.
        :rtype: bool
        """
        pass

    @staticmethod
    @abstractmethod
    def get_extra_config_sample():
        """
        Returns a sample extra configuration for this service (if necessary
        :return: A dictionary that represents the sample extra configuration.
        :rtype: dict
        """
        pass

    @abstractmethod
    def is_valid_extra_config(self, config):
        """
        Checks if the given configuration is valid.

        :param config: The extra configuration for this service
        :type config: dict
        :return: True if the configuration is valid, False otherwise.
        :rtype: bool
        """
        pass

    # region installation methods
    @staticmethod
    @abstractmethod
    def get_apt_dependencies():
        """
        Gets a list of the dependencies which need to be installed through
        apt-get. No configuration is possible (a.k.a. silent install is
        only possible).

        :return: A list of the dependencies that need to be installed
            through apt-get.
        :rtype: list[str]
        """
        return []

    @staticmethod
    @abstractmethod
    def get_pip_dependencies():
        """
        Gets a list of the dependencies which need to be installed through
        pip. No configuration is possible (a.k.a. silent install is only
        possible).

        :return: A list of the dependencies that need to be installed
            through pip.
        :rtype: list[str]
        """
        return []

    @staticmethod
    @abstractmethod
    def after_install_hook():
        """
        Runs any necessary post-install operations (e.g. modifying config
        files).

        :return: True on success, false on failure
        :rtype: bool
        """
        return False
    # endregion
