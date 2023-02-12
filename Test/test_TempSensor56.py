import lib.TempSensor as TempSensor
import time
from test_configs import max31856hardware as config

# Requires a board connected to a MAX31856 and thermocouple using hardware SPI pins


def test_sim():
    sim_ts = TempSensor.SimulatedBoard(config)

    temp = sim_ts.temp_sensor.temperature()

    assert type(temp) is int
    assert temp == 65


def test_raw_temp():
    brd = TempSensor.RealBoard(config)

    temp = brd.temp_sensor.raw_temp()

    assert type(temp) is float
    assert temp > 10


def test_all_slow():
    brd = TempSensor.RealBoard(config)

    time.sleep(2)

    temp = brd.temp_sensor.temperature()
    temps = brd.temp_sensor.temptracker.temps

    print(str(temps))

    assert type(temp) is float
    assert temp > 9
    assert len(temps) == 10

    count = 0
    for t in temps:
        if t > 0:
            count += 1
    assert count > 1  # This tests the thread ran

