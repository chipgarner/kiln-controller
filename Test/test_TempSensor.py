import lib.TempSensor as TempSensor


def test_sim():
    sim_ts = TempSensor.SimulatedBoard()

    temp = sim_ts.temp_sensor.temperature()

    assert temp == 65


def test_me():
    max56 = TempSensor.Max31856()


def test_it():
    sim_ts = TempSensor.RealBoard()
