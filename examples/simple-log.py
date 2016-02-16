from picolog.hrdl.adc import PicoLogAdc
from picolog.constants import Handle, Channel, Status, Info, \
Error, SettingsError, Progress, VoltageRange, InputType, ConversionTime, \
SampleMethod

adc = PicoLogAdc()
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
    adc.set_sample_time(1500, ConversionTime.TIME_340MS)
    adc.stream()

    import csv
    with open("data.csv", "a") as f:
        writer = csv.writer(f, delimiter=",")

        while True:
            if adc.ready():
                #print(i)
                #print("ADC ready to retrieve values")
                (stimes, svalues) = adc.get_samples()
                if stimes:
                    print(svalues)
                    #print(stimes, adc.counts_to_volts(svalues, Channel.ANALOG_CHANNEL_1))
                    #data = [stimes[0], adc.counts_to_volts(svalues, Channel.ANALOG_CHANNEL_1)[0]]
                    #writer.writerows([data])
                    #times.extend(stimes)
                    #values.extend(adc.counts_to_volts(svalues, Channel.ANALOG_CHANNEL_15))
            time.sleep(1.5)
        adc.close_unit()
except KeyboardInterrupt:
    adc.close_unit()
except:
    adc.close_unit()
    raise
