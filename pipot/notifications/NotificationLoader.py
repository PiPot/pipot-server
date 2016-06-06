import importlib
import os
from traceback import print_exc

import pipot.notifications as main
import pipot.notifications.temp as temp
from pipot.notifications.INotification import INotification


class NotificationLoaderException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def load_from_file(file_name, temp_folder=True):
    """
    Gets a class name from a given file.

    :param file_name: The file name to open and look in.
    :type file_name: str
    :param temp_folder: Is the file located in the temp folder?
    :type temp_folder: bool
    :return: A class name of the found class.
    :rtype: class
    """
    mod_name, file_ext = os.path.splitext(os.path.split(file_name)[-1])

    try:
        py_mod = importlib.import_module(
            '.' + mod_name,
            temp.__name__ if temp_folder else main.__name__)

        if hasattr(py_mod, mod_name):
            cls = getattr(py_mod, mod_name)
        else:
            raise NotificationLoaderException('There is no class named %s '
                                              'present in the file' %
                                              mod_name)

        if INotification in cls.__bases__:
            return cls
    except TabError as e:
        print_exc()
        raise NotificationLoaderException('Tab error: %s' % str(e))
    except TypeError as e:
        print_exc()
        raise NotificationLoaderException('Validation of the imported file '
                                          'failed: %s' % str(e))
    except ImportError as e:
        print_exc()
        raise NotificationLoaderException('Import of the file  failed: %s'
                                          % str(e))

    raise NotificationLoaderException('File does not contain a valid '
                                      'INotification implementation')


def get_class_instance(name, config):
    """
    Gets an instance of the given class name (a service in this folder).

    :param name: The name of the class we want an instance of.
    :type name: str
    :param config: The configuration for this service
    :type config: dict
    :return: A class instance of the loaded class.
    :rtype: pipot.notifications.INotification.INotification
    """
    try:
        py_mod = importlib.import_module('.' + name, main.__name__)

        if hasattr(py_mod, name):
            class_inst = getattr(py_mod, name)(config=config)
        else:
            raise NotificationLoaderException('There is no class named %s '
                                              'present in the file' % name)

        if isinstance(class_inst, INotification):
            return class_inst
    except TabError as e:
        raise NotificationLoaderException('Tab error: %s' % str(e))
    except TypeError as e:
        raise NotificationLoaderException('Validation of the imported file '
                                          'failed: %s' % str(e))
    except ImportError as e:
        raise NotificationLoaderException('Import of the file failed: %s' %
                                          str(e))

    raise NotificationLoaderException('File does not contain a valid '
                                      'INotification implementation')
