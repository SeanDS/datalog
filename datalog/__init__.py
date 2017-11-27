"""DataLog module"""

import logging

__author__ = "Sean Leavey <datalog@attackllama.com>"
__version__ = "0.7.7"

# suppress warnings when the user code does not include a handler
logging.getLogger().addHandler(logging.NullHandler())
