# pylint: disable=missing-module-docstring

import unittest
import re
from src.libretto import OutVal
from src.libretto import SearchConditional

class TestSearchConditional(unittest.TestCase):
    # pylint: disable=missing-class-docstring

    def test_match(self):
        # pylint: disable=missing-function-docstring, no-self-use
        pattern = "bcd"
        regex = re.escape(pattern)
        out = OutVal()

        result = SearchConditional.search(out, regex, "abcde")

        match = out.value
        matchval = match.group(0)
        matchstart = match.start(0)
        matchend = match.end(0)

        assert result, "unexpected result"
        assert match, "requires a match"
        assert matchval == "bcd", "expected to match full regex"
        assert matchstart == 1, "match started in wrong position"
        assert matchend == 4, "match ended in wrong position"

    def test_no_match(self):
        # pylint: disable=missing-function-docstring, no-self-use
        pattern = "bcd"
        regex = re.escape(pattern)
        out = OutVal()

        result = SearchConditional.search(out, regex, "xyz")

        match = out.value

        assert not result, "unexpected result"
        assert not match, "should be no match"

if __name__ == '__main__':
    unittest.main()
