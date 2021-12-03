from fuo_ytmusic import timeparse


def test_timeparse():
    assert isinstance(timeparse.timeparse('3:05'), int)
    assert timeparse.timeparse('3:05') == 185
    assert isinstance(timeparse.timeparse('05:30'), int)
    assert timeparse.timeparse('05:30') == 330
    assert isinstance(timeparse.timeparse('5 minutes, 14 seconds'), int)
    assert timeparse.timeparse('5 minutes, 14 seconds') == 314
