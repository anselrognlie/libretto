#!/usr/local/bin/python3

import sys
sys.path.append('../src')

import unittest
from libretto import Track
from libretto import Line
from libretto import LineType

class TestTrack(unittest.TestCase):
  
  def test_TrackInitialization(self):
    track = Track(1, 2, 3)
    length = track.length

    assert track.trackNo == 1, "unexpected track number"
    assert length.days == 0, "unexpected days"
    assert length.seconds == 123, "unexpected seconds"
    assert length.microseconds == 0, "unexpected microseconds"
    assert len(track.lines) == 0, "should have no lines"
  
  def test_TrackSetLength(self):
    track = Track()
    track.setLength(2, 3)
    length = track.length

    assert track.trackNo == 0, "unexpected track number"
    assert length.days == 0, "unexpected days"
    assert length.seconds == 123, "unexpected seconds"
    assert length.microseconds == 0, "unexpected microseconds"
    assert len(track.lines) == 0, "should have no lines"

  def test_TrackAddLine(self):
    track = Track()
    line = Line(LineType.SCENE, "text", "subtext")
    track.addLine(line)

    assert track.trackNo == 0, "unexpected track number"
    assert len(track.lines) == 1, "should have no lines"

    storedLine = track.lines[0]

    assert storedLine.type == LineType.SCENE, "type mismatch"
    assert storedLine.text == "text", "text mismatch"
    assert storedLine.subtext == "subtext", "subtext mismatch"

if __name__ == '__main__':
  unittest.main()
