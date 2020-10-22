# pylint: disable=missing-module-docstring

import unittest
from src.libretto import Line
from src.libretto import LineType

class TestLine(unittest.TestCase):
    # pylint: disable=missing-class-docstring
    def test_line_initialization(self):
        # pylint: disable=no-self-use, missing-function-docstring
        line = Line(LineType.SCENE, "text", "subtext")

        assert line.type == LineType.SCENE, "type mismatch"
        assert line.text == "text", "text mismatch"
        assert line.subtext == "subtext", "subtext mismatch"

if __name__ == '__main__':
    unittest.main()
