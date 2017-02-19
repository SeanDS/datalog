import os.path
from configparser import ConfigParser
import logging

THIS_DIR = os.path.dirname(os.path.realpath(__file__))


class AdcConfig(ConfigParser):
    DEFAULT_CONFIG_PATH = os.path.join(THIS_DIR, 'adc.conf')

    def __init__(self, path=None, *args, **kwargs):
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

        # server config
        self['server'] = {
            'host': 'localhost',
            'port': '50000',
            'max_connections': '5',
            'socket_buf_len': '1000',
            'max_readings_per_request': '1000'
        }

        # retriever settings
        self['retriever'] = {
            # time to wait between ADC polls (ms)
            'poll_rate': '10000'
        }

        # library paths
        self['picolog'] = {
            'lib_path_adc24': '/opt/picoscope/lib/libpicohrdl.so'
        }

        if path is None:
            path = self.DEFAULT_CONFIG_PATH

        with open(path) as f:
            logging.getLogger("config").debug("Reading config from {0}".format(path))
            self.read_file(f)
