#!/usr/local/bin/python3

import sys
sys.path.append('../src')

import unittest
from libretto import LineType

class TestLineType(unittest.TestCase):
  
  def test_TypeRange(self):

    assert LineType.UNKNOWN == 0, "UNKNOWN == 0"
    assert LineType.SCENE == 1, "SCENE = 1"
    assert LineType.SDETAILS == 2, "SDETAILS = 2"
    assert LineType.STAGING == 3, "STAGING = 3"
    assert LineType.CHARACTER == 4, "CHARACTER = 4"
    assert LineType.LYRIC == 5, "LYRIC = 5"
    assert LineType.EMOTE == 6, "EMOTE = 6"
    assert LineType.BLANK == 8, "BLANK = 8"
    assert LineType.MAX == LineType.BLANK, "BLANK is the last type"

  def test_TypePrinting(self):

    assert LineType.toStr(LineType.UNKNOWN) == "UNKNOWN", "unexpected string version"
    assert LineType.toStr(LineType.SCENE) == "SCENE", "unexpected string version"
    assert LineType.toStr(LineType.SDETAILS) == "SDETAILS", "unexpected string version"
    assert LineType.toStr(LineType.STAGING) == "STAGING", "unexpected string version"
    assert LineType.toStr(LineType.CHARACTER) == "CHARACTER", "unexpected string version"
    assert LineType.toStr(LineType.LYRIC) == "LYRIC", "unexpected string version"
    assert LineType.toStr(LineType.EMOTE) == "EMOTE", "unexpected string version"
    assert LineType.toStr(LineType.BLANK) == "BLANK", "unexpected string version"
    assert LineType.toStr(LineType.MAX) == "BLANK", "unexpected string version"

if __name__ == '__main__':
  unittest.main()
