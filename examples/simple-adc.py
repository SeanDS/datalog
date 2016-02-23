import sys
import time
import logging

from picolog.hrdl.adc import PicoLogAdc
from picolog.constants import Handle, Channel, Status, Info, \
Error, SettingsError, Progress, VoltageRange, InputType, ConversionTime, \
SampleMethod

syslogger = logging.getLogger('Logger')

adc = PicoLogAdc("/opt/picoscope/lib/libpicohrdl.so", 1000, 10, logger=syslogger)

try:
    adc.open_unit_with_progress()
    adc.set_analog_in_channel(Channel.ANALOG_CHANNEL_1, True, \
    VoltageRange.RANGE_2500_MV, InputType.SINGLE)
    adc.set_analog_in_channel(Channel.ANALOG_CHANNEL_2, True, \
    VoltageRange.RANGE_2500_MV, InputType.SINGLE)
    adc.set_analog_in_channel(Channel.ANALOG_CHANNEL_3, True, \
    VoltageRange.RANGE_2500_MV, InputType.SINGLE)
    adc.set_analog_in_channel(Channel.ANALOG_CHANNEL_4, True, \
    VoltageRange.RANGE_2500_MV, InputType.SINGLE)
    print("Enabled channels: {0}".format(adc.get_enabled_channels_count()))
    adc.set_sample_time(5000, ConversionTime.TIME_340MS)
    adc.stream()

    while True:
        if adc.ready():
            payload = adc._get_payload()
            print(payload)
        time.sleep(5)
    adc.close_unit()
except KeyboardInterrupt:
    adc.close_unit()
except:
    adc.close_unit()
    raise
