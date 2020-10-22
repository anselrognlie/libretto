# pylint: disable=missing-module-docstring

import unittest
from src.libretto import Track
from src.libretto import Line
from src.libretto import LineType

class TestTrack(unittest.TestCase):
    # pylint: disable=missing-class-docstring

    def test_track_initialization(self):
        # pylint: disable=missing-function-docstring, no-self-use
        track = Track(1, 2, 3)
        length = track.length

        assert track.track_number == 1, "unexpected track number"
        assert length.days == 0, "unexpected days"
        assert length.seconds == 123, "unexpected seconds"
        assert length.microseconds == 0, "unexpected microseconds"
        assert len(track.lines) == 0, "should have no lines"

    def test_track_set_length(self):
        # pylint: disable=missing-function-docstring, no-self-use
        track = Track()
        track.set_length(2, 3)
        length = track.length

        assert track.track_number == 0, "unexpected track number"
        assert length.days == 0, "unexpected days"
        assert length.seconds == 123, "unexpected seconds"
        assert length.microseconds == 0, "unexpected microseconds"
        assert len(track.lines) == 0, "should have no lines"

    def test_track_add_line(self):
        # pylint: disable=missing-function-docstring, no-self-use
        track = Track()
        line = Line(LineType.SCENE, "text", "subtext")
        track.add_line(line)

        assert track.track_number == 0, "unexpected track number"
        assert len(track.lines) == 1, "should have no lines"

        stored_line = track.lines[0]

        assert stored_line.type == LineType.SCENE, "type mismatch"
        assert stored_line.text == "text", "text mismatch"
        assert stored_line.subtext == "subtext", "subtext mismatch"

if __name__ == '__main__':
    unittest.main()
