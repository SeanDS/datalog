"""Configuration parser and defaults"""

import os.path
import logging
import abc
from configparser import ConfigParser
import pkg_resources
import appdirs

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

# logger
logger = logging.getLogger("datalog.config")


class BaseConfig(ConfigParser, metaclass=abc.ABCMeta):
    """Base config parser"""

    def __init__(self, *args, **kwargs):
        super(BaseConfig, self).__init__(*args, **kwargs)

        # server config
        self['server'] = {
            'host': 'localhost',
            'port': '8080',
            'max_connections': '5',
            'socket_buf_len': '1000',
            'default_readings_per_request': '100',
            'max_readings_per_request': '1000',
            'default_format': 'json'
        }


class AdcConfig(BaseConfig):
    """ADC config parser"""

    DEFAULT_CONFIG_FILENAME = 'adc.conf.dist'

    def __init__(self, *args, **kwargs):
        super(AdcConfig, self).__init__(*args, **kwargs)

        # device config
        self['device'] = {
            'str_buf_len': '1000',
            'sample_buf_len': '1000',
            'sample_time': '1000',
            'conversion_time': '4'
        }

        # ADC config
        self['adc'] = {
            'type': 'PicoLog24'
        }

        # retriever settings
        self['fetch'] = {
            # time to wait between ADC polls (ms)
            'poll_time': '10000'
        }

        # library paths
        self['picolog'] = {
            'lib_path_adc24': '/opt/picoscope/lib/libpicohrdl.so'
        }

        self.load_config_file()

    def load_config_file(self):
        path = self.get_config_filepath()

        with open(path) as obj:
            logger.debug("Reading config from %s", path)
            self.read_file(obj)

    @classmethod
    def get_config_filepath(cls):
        """Find the path to the config file

        This creates the config file if it does not exist, using the distributed
        template.
        """

        config_dir = appdirs.user_config_dir("datalog")
        config_file = os.path.join(config_dir, "adc.conf")

        # check the config file exists
        if not os.path.isfile(config_file):
            cls.create_user_config_file(config_file)

        return config_file

    @classmethod
    def create_user_config_file(cls, config_file):
        """Create config file in user directory"""

        directory = os.path.dirname(config_file)

        # create user config directory
        if not os.path.exists(directory):
            os.makedirs(directory)

        logger.debug("Creating config file at %s", directory)

        # copy across distribution template
        with open(config_file, 'wb') as user_file:
            # find distribution config file and copy it to the user config file
            user_file.writelines(
                pkg_resources.resource_stream(__name__,
                                              cls.DEFAULT_CONFIG_FILENAME)
            )
