#!/usr/local/bin/python3

import sys
sys.path.append('../src')

import unittest
from libretto import Line
from libretto import LineType

class TestLine(unittest.TestCase):
  
  def test_LineInitialization(self):
    line = Line(LineType.SCENE, "text", "subtext")

    assert line.type == LineType.SCENE, "type mismatch"
    assert line.text == "text", "text mismatch"
    assert line.subtext == "subtext", "subtext mismatch"

if __name__ == '__main__':
  unittest.main()
