import busio
import bitbangio
import statistics
import logging
import threading
import digitalio
import time
from abc import ABC

log = logging.getLogger(__name__)


# wrapper for blinka board
class Board():
    """This represents a blinka board where this code
    runs.
    """

    def __init__(self):
        log.info("board: %s" % self.name)
        self.temp_sensor.start()


class RealBoard(Board):
    """Each board has a thermocouple board attached to it.
    Any blinka board that supports SPI can be used. The
    board is automatically detected by blinka.
    """

    def __init__(self, config):
        self.config = config
        self.name = None
        self.load_libs()
        self.temp_sensor = self.choose_tempsensor()
        Board.__init__(self)

    def load_libs(self):
        import board
        self.name = board.board_id


    def choose_tempsensor(self):
        if self.config.max31855:
            return Max31855()
        if self.config.max31856:
            return Max31856()


class SimulatedBoard(Board):
    """Simulated board used during simulations.
    See config.simulate
    """

    def __init__(self, config):
        self.name = "simulated"
        self.temp_sensor = TempSensorSimulated(config)
        Board.__init__(self)


class TempSensor(threading.Thread):
    """Used by the Board class. Each Board must have
    a TempSensor.
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.time_step = self.config.sensor_time_wait
        self.status = ThermocoupleTracker(self.config.temperature_average_samples)


class TempSensorSimulated(TempSensor):
    """Simulates a temperature sensor """

    def __init__(self, config):
        self.config = config
        TempSensor.__init__(self)
        self.simulated_temperature = self.config.sim_t_env

    def temperature(self):
        return self.simulated_temperature


class TempSensorReal(TempSensor):
    """real temperature sensor that takes many measurements
       during the time_step
       inputs
           config.temperature_average_samples
    """

    def __init__(self):
        TempSensor.__init__(self)
        self.sleeptime = self.time_step / float(self.config.temperature_average_samples)
        self.temptracker = TempTracker()
        self.spi = busio.SPI(self.config.spi_sclk, self.config.spi_mosi, self.config.spi_miso)
        self.cs = digitalio.DigitalInOut(self.config.spi_cs)

    def get_temperature(self):
        """read temp from tc and convert if needed"""
        try:
            temp = self.raw_temp()  # raw_temp provided by subclasses
            if self.config.temp_scale.lower() == "f":
                temp = (temp * 9 / 5) + 32
            self.status.good()
            return temp
        except ThermocoupleError as tce:
            if tce.ignore:
                log.error("Problem reading temp (ignored) %s" % tce.message)
                self.status.good()
            else:
                log.error("Problem reading temp %s" % tce.message)
                self.status.bad()
        return None

    def temperature(self):
        """average temp over a duty cycle"""
        return self.temptracker.get_avg_temp()

    def run(self):
        while True:
            temp = self.get_temperature()
            if temp:
                self.temptracker.add(temp)
            time.sleep(self.sleeptime)


class TempTracker:
    """creates a sliding window of N temperatures per
       config.sensor_time_wait
    """

    def __init__(self, temperature_average_samples):
        self.size = temperature_average_samples
        self.temps = [0 for i in range(self.size)]

    def add(self, temp):
        self.temps.append(temp)
        while len(self.temps) > self.size:
            del self.temps[0]

    def get_avg_temp(self):
        """
        take the median of the given values. this used to take an avg
        after getting rid of outliers. median works better.
        """
        return statistics.median(self.temps)


class ThermocoupleTracker:
    """Keeps sliding window to track successful/failed calls to get temp
       over the last two duty cycles.
    """

    def __init__(self, temperature_average_samples):
        self.size = temperature_average_samples * 2
        self.status = [True for i in range(self.size)]
        self.limit = 30

    def good(self):
        """True is good!"""
        self.status.append(True)
        del self.status[0]

    def bad(self):
        """False is bad!"""
        self.status.append(False)
        del self.status[0]

    def error_percent(self):
        errors = sum(i == False for i in self.status)
        return (errors / self.size) * 100

    def over_error_limit(self):
        if self.error_percent() > self.limit:
            return True
        return False


class Max31855(TempSensorReal):
    """each subclass expected to handle errors and get temperature"""

    def __init__(self, config):
        self.config = config
        TempSensorReal.__init__(self)
        log.info("thermocouple MAX31855")
        import adafruit_max31855
        self.thermocouple = adafruit_max31855.MAX31855(self.spi, self.cs)

    def raw_temp(self):
        try:
            return self.thermocouple.temperature_NIST
        except RuntimeError as rte:
            if rte.args and rte.args[0]:
                raise Max31855_Error(rte.args[0])
            raise Max31855_Error('unknown')


class ThermocoupleError(Exception):
    """
    thermocouple exception parent class to handle mapping of error messages
    and make them consistent across adafruit libraries. Also set whether
    each exception should be ignored based on settings in config.py.
    """

    def __init__(self, message):
        self.ignore = False
        self.message = message
        self.map_message()
        self.set_ignore()
        super().__init__(self.message)

    def set_ignore(self):
        if self.message == "not connected" and self.config.ignore_tc_lost_connection == True:
            self.ignore = True
        if self.message == "short circuit" and self.config.ignore_tc_short_errors == True:
            self.ignore = True
        if self.message == "unknown" and self.config.ignore_tc_unknown_error == True:
            self.ignore = True
        if self.message == "cold junction range fault" and self.config.ignore_tc_cold_junction_range_error == True:
            self.ignore = True
        if self.message == "thermocouple range fault" and self.config.ignore_tc_range_error == True:
            self.ignore = True
        if self.message == "cold junction temp too high" and self.config.ignore_tc_cold_junction_temp_high == True:
            self.ignore = True
        if self.message == "cold junction temp too low" and self.config.ignore_tc_cold_junction_temp_low == True:
            self.ignore = True
        if self.message == "thermocouple temp too high" and self.config.ignore_tc_temp_high == True:
            self.ignore = True
        if self.message == "thermocouple temp too low" and self.config.ignore_tc_temp_low == True:
            self.ignore = True
        if self.message == "voltage too high or low" and self.config.ignore_tc_voltage_error == True:
            self.ignore = True

    def map_message(self):
        try:
            self.message = self.map[self.orig_message]
        except KeyError:
            self.message = "unknown"


class Max31855_Error(ThermocoupleError):
    """
    All children must set self.orig_message and self.map
    """

    def __init__(self, message):
        self.orig_message = message
        # this purposefully makes "fault reading" and
        # "Total thermoelectric voltage out of range..." unknown errors
        self.map = {
            "thermocouple not connected": "not connected",
            "short circuit to ground": "short circuit",
            "short circuit to power": "short circuit",
        }
        super().__init__(message)


class Max31856_Error(ThermocoupleError):
    def __init__(self, message):
        self.orig_message = message
        self.map = {
            "cj_range": "cold junction range fault",
            "tc_range": "thermocouple range fault",
            "cj_high": "cold junction temp too high",
            "cj_low": "cold junction temp too low",
            "tc_high": "thermocouple temp too high",
            "tc_low": "thermocouple temp too low",
            "voltage": "voltage too high or low",
            "open_tc": "not connected"
        }
        super().__init__(message)


class Max31856(TempSensorReal):
    """each subclass expected to handle errors and get temperature"""

    def __init__(self, config):
        self.config = config
        TempSensorReal.__init__(self)
        log.info("thermocouple MAX31856")
        import adafruit_max31856
        self.thermocouple = adafruit_max31856.MAX31856(self.spi, self.cs,
                                                       thermocouple_type=self.config.thermocouple_type)
        if self.config.ac_freq_50hz:
            self.thermocouple.noise_rejection = 50
        else:
            self.thermocouple.noise_rejection = 60

    def raw_temp(self):
        # The underlying adafruit library does not throw exceptions
        # for thermocouple errors. Instead, they are stored in
        # dict named self.thermocouple.fault. Here we check that
        # dict for errors and raise an exception.
        # and raise Max31856_Error(message)
        temp = self.thermocouple.temperature
        for k, v in self.thermocouple.fault.items():
            if v:
                log.warning('31856 error: ' + str(k))
                raise Max31856_Error(k)
        return temp
