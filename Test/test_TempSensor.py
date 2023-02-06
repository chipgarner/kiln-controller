import lib.TempSensor as TempSensor


def test_sim():
    sim_ts = TempSensor.SimulatedBoard()

    temp = sim_ts.temp_sensor.temperature()

    assert temp == 65


def test_me():
    max56 = TempSensor.Max31856()

    temp = max56.raw_temp()

    assert temp == 7


def test_it():
    brd = TempSensor.RealBoard()

    temp = brd.temp_sensor.temperature()

    assert temp == 9
