import importlib
import os
import sys

from pipot.services.IService import IService
import pipot.services as main
import pipot.services.temp as temp


class ServiceLoaderException(Exception):
    """
    Class for service loader exceptions
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def load_from_container(container_dir, temp_folder=False, re_load=False):
    """Attempts to load the service from a folder with the same name
    Required container format:
    myService.zip
    |-myService.py
    |-__init__.py (will be created if doesn't exist)
    |-requirement.txt (optional)
    |-other file/folder

    :param container_dir: The path of container
    :type container_dir: str
    :return: A class instance of the loaded class.
    :rtype: pipot.services.IService.IService
    """
    mod_name = os.path.split(container_dir)[-1]
    mod_file = os.path.join(container_dir, mod_name + '.py')
    if not os.path.isfile(mod_file):
        raise ServiceLoaderException('There is no service file %s.py found inside container' % mod_name)
    else:
        if os.path.isfile(os.path.join(container_dir, 'requirement.txt')):
            # TODO: ideally add check on pip install
            pass
        if not os.path.isfile(os.path.join(container_dir, '__init__.py')):
            open(os.path.join(container_dir, '__init__.py'), 'w')
        instance = load_from_file(mod_file, temp_folder=temp_folder, re_load=re_load)
        return instance


def load_from_file(file_name, temp_folder=True, re_load=False):
    """
    Attempts to load a given class from a file with the same name in this
    folder.

    :param file_name: The name of the file to load (including file extension)
    :type file_name: str
    :param temp_folder: Is the file located in the temporary folder?
    :type temp_folder: bool
    :return: A class instance of the loaded class.
    :rtype: pipot.services.IService.IService
    """
    mod_name, file_ext = os.path.splitext(os.path.split(file_name)[-1])

    try:
        if re_load:
            try:
                del sys.modules['pipot.services.' + mod_name]
                del sys.modules['pipot.services.' + mod_name + '.' + mod_name]
            except KeyError:
                pass
        py_mod = importlib.import_module('pipot.services.' + mod_name + '.' + mod_name)
        if hasattr(py_mod, mod_name):
            class_inst = getattr(py_mod, mod_name)(None, None)
        else:
            raise ServiceLoaderException('There is no class named %s '
                                         'present in the file' % mod_name)

        if isinstance(class_inst, IService):
            return class_inst
    except TabError as e:
        raise ServiceLoaderException('Tab error: %s' % str(e))
    except TypeError as e:
        raise ServiceLoaderException('Validation of the imported file '
                                     'failed: %s' % str(e))
    except ImportError as e:
        raise ServiceLoaderException('Import of the file '
                                     'failed: %s' % str(e))

    raise ServiceLoaderException('File does not contain a valid IService  '
                                 'implementation')


def get_class_instance(name, collector, config):
    """
    Gets an instance of the given class name (a service in this folder).

    :param name: The name of the class we want an instance of.
    :type name: str
    :param collector: The instance of the collector that gathers the
        messages, groups them and sends them to the server instance.
    :type collector: serverCollector.ICollector
    :param config: The configuration for this service
    :type config: dict
    :return: A class instance of the loaded class.
    :rtype: pipot.services.IService.IService
    """
    try:
        py_mod = importlib.import_module('.' + name, main.__name__)

        if hasattr(py_mod, name):
            class_inst = getattr(py_mod, name)(collector=collector,
                                               config=config)
        else:
            raise ServiceLoaderException('There is no class named %s '
                                         'present in the file' % name)

        if isinstance(class_inst, IService):
            return class_inst
    except TabError as e:
        raise ServiceLoaderException('Tab error: %s' % str(e))
    except TypeError as e:
        raise ServiceLoaderException('Validation of the imported file '
                                     'failed: %s' % str(e))
    except ImportError as e:
        raise ServiceLoaderException('Import of the file '
                                     'failed: %s' % str(e))

    raise ServiceLoaderException('File does not contain a valid IService  '
                                 'implementation')
