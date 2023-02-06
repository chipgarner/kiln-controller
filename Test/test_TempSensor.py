import lib.TempSensor as TempSensor
import time


def test_sim():
    sim_ts = TempSensor.SimulatedBoard()

    temp = sim_ts.temp_sensor.temperature()

    assert temp == 65


def test_me():
    max56 = TempSensor.Max31856()

    temp = max56.raw_temp()

    assert type(temp) is float
    assert temp > 10


def test_it():
    brd = TempSensor.RealBoard()

    time.sleep(10)

    temp = brd.temp_sensor.temperature()

    assert type(temp) is float
    assert temp == 9
