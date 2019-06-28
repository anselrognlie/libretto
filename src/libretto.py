#!/usr/local/bin/python3

from __future__ import print_function
import types
import datetime

BIN = None

class OutVal:
    def __init__(self):
        self.value = None

class SearchConditional:
    def __init__(self):
        pass

    @classmethod
    def search(classType, outval, regex, str):
        import re
        match = re.search(regex, str)
        outval.value = match
        return match != None

class LineType:
    UNKNOWN = 0
    SCENE = 1
    SDETAILS = 2
    STAGING = 3
    CHARACTER = 4
    LYRIC = 5
    EMOTE = 6
    BLANK = 8
    MAX = BLANK

    @classmethod
    def toStr(classType, lineType):
        if lineType == LineType.UNKNOWN:
            return "UNKNOWN"
        elif lineType == LineType.SCENE:
            return "SCENE"
        elif lineType == LineType.SDETAILS:
            return "SDETAILS"
        elif lineType == LineType.STAGING:
            return "STAGING"
        elif lineType == LineType.CHARACTER:
            return "CHARACTER"
        elif lineType == LineType.LYRIC:
            return "LYRIC"
        elif lineType == LineType.EMOTE:
            return "EMOTE"
        elif lineType == LineType.BLANK:
            return "BLANK"

class ParseMode:
    BEGIN = 0
    LINE = 1
    INTRACK = 2
    INSCENE = 3
    INLYRIC = 4

class Line:
    def __init__(self, type, text=None, subtext=None):
        self.type = type
        self.text = text
        self.subtext = subtext

class Track:
    def __init__(self, trackNo=0, min=0, sec=0):
        self.trackNo = trackNo
        self.length = datetime.timedelta(minutes=min, seconds=sec)
        self.lines = []
        self.subtracks = []
        self.parent = None

    def setLength(self, min, sec):
        self.length = datetime.timedelta(minutes=min, seconds=sec)

    def addLine(self, line):
        self.lines.append(line)

    def addSubtrack(self, track):
        track.parent = self
        self.subtracks.append(track)

class LibrettoLoader:
    def __init__(self):
        self.filename = None
        self.libretto = None
        self.parseMode = None
        self.track = 0
        self.currentTrack = None
        self.tracks = []
        self.error = False
        self.errorLineNo = 0
        self.errorLine = None
        self.errorMsg = None
        self.lineNo = 0

    def load(self, filename):
        self.filename = filename
        return self._doLoad()

    def _resetParseState(self):
        self.parseMode = ParseMode.BEGIN
        self.track = 0
        self.currentTrack = None
        self.lineNo = 0
        self.error = False

    def _doLoad(self):
        self._resetParseState()

        with open(self.filename) as f:
            for line in f:
                self.lineNo += 1

                # trim any whitespace
                line = line.strip()
                end = self._processLine(line)
                if end:
                    break

        self.libretto = Libretto(self.tracks)
        return self.libretto

    def _processINSCENE(self, line):
        match = None

        # if blank, this is the end of the scene
        if len(line) == 0:
            self.parseMode = ParseMode.INTRACK
            return self._processBLANK()
        else:
            self.currentTrack.addLine(Line(LineType.SDETAILS, line))

        return self.error


    def _processSCENE(self, text):
        self.parseMode = ParseMode.INSCENE
        line = Line(LineType.SCENE, text)
        self.currentTrack.addLine(line)

        return self.error

    def _processSTAGING(self, text):
        line = Line(LineType.STAGING, text)
        self.currentTrack.addLine(line)

        return self.error

    def _processBLANK(self):
        line = Line(LineType.BLANK)
        self.currentTrack.addLine(line)

        return self.error

    def _processCHARACTER(self, name, emote=None):
        self.parseMode = ParseMode.INLYRIC
        line = Line(LineType.CHARACTER, name, emote)
        self.currentTrack.addLine(line)

        return self.error

    def _processINTRACK(self, line):
        outval = OutVal()

        # is it a scene title? e.g. PROLOGUE[: blah blah]
        if SearchConditional.search(outval,
            r"^[A-Z0-9 ]+$|^[A-Z0-9 ]+:.*$", line):
            
            return self._processSCENE(line)

        # is it a blank line? ignore
        elif len(line) == 0:
            return self._processBLANK()

        # look for a track header e.g. [#,##:##]
        elif self.isTRACKLINE(outval, line):
            return outval.value

        # look for a subtrack header e.g. [##:##]
        elif self.isSUBTRACKLINE(outval, line):
            return outval.value

        # is it a character line?  e.g. Steve: [emote]
        elif SearchConditional.search(outval, r"^([^:]+):$", line):
            match = outval.value
            return self._processCHARACTER(match.group(1))

        elif SearchConditional.search(outval, r"^([^:]+): \[(.*)\]$", line):
            match = outval.value
            return self._processCHARACTER(match.group(1), match.group(2))

        # does it contain emotes?  e.g. [does something]
        elif self.isEMOTELINE(outval, line):
            return outval.value

        # is it flavor text?  e.g. some long text that wraps around
        elif len(line) > 40:
            return self._processSTAGING(line)

        # just a regular lyric
        else:
            return self._processLYRIC(line)

        return self.error

    def _processTRACKLINE(self, track, min, sec, line):
        trackNo = int(track)
        track = Track(trackNo, int(min), int(sec))
        self.track = trackNo
        self.tracks.append(track)
        self.currentTrack = track

        # if we found the track mid lyric, stay in lyric mode
        if self.parseMode == ParseMode.INLYRIC:
            return self._processINLYRIC(line)
        else:
            self.parseMode = ParseMode.INTRACK
            return self._processINTRACK(line)

    def _processSUBTRACKLINE(self, min, sec, line):
        # addd this subtrack, but if the current track is already a subtrack,
        # move up to the parent track first
        if self.currentTrack.parent is not None:
            self.currentTrack = self.currentTrack.parent

        subtrackId = len(self.currentTrack.subtracks)
        track = Track(f"{self.currentTrack.trackNo}.{subtrackId}", 
            int(min), int(sec))

        self.currentTrack.addSubtrack(track)
        self.currentTrack = track

        # if we found the track mid lyric, stay in lyric mode
        if self.parseMode == ParseMode.INLYRIC:
            return self._processINLYRIC(line)
        else:
            self.parseMode = ParseMode.INTRACK
            return self._processINTRACK(line)

    def _processBEGIN(self, line):
        outval = OutVal()

        # skip a blank line
        if len(line) == 0:
            pass
        # look for a track header e.g. [#,##:##]
        elif self.isTRACKLINE(outval, line):
            return outval.value
        else:
            # error
            self._setError("unexpected input looking for track",
                self.lineNo, line)

        return self.error

    def isTRACKLINE(self, outval, line):
        matchOutVal = OutVal()
        doesMatch = SearchConditional.search(matchOutVal,
            r"^\[(\d+),(\d+):(\d+)\](.*)", line)
        if doesMatch:
            match = matchOutVal.value
            outval.value = self._processTRACKLINE(match.group(1),
                match.group(2), match.group(3), match.group(4).strip())

        return doesMatch

    def isSUBTRACKLINE(self, outval, line):
        matchOutVal = OutVal()
        doesMatch = SearchConditional.search(matchOutVal,
            r"^\[(\d+):(\d+)\](.*)", line)
        if doesMatch:
            match = matchOutVal.value
            outval.value = self._processSUBTRACKLINE(match.group(1),
                match.group(2), match.group(3).strip())

        return doesMatch

    def isEMOTELINE(self, outval, line):
        matchOutVal = OutVal()
        doesMatch = SearchConditional.search(matchOutVal,
            r"^\[(.*)\]$", line)
        if doesMatch:
            match = matchOutVal.value
            outval.value = self._processEMOTE(match.group(1))
        # make sure it wasn't malformed (multiline)
        elif SearchConditional.search(outval, r"^\[([^]]*)$", line):
            doesMatch = True
            self._setError("malformed emote", self.lineNo, line)
            outval.value = self.error

        return doesMatch

    def _processEMOTE(self, text):
        self.parseMode = ParseMode.INLYRIC
        line = Line(LineType.EMOTE, text)
        self.currentTrack.addLine(line)

        return self.error

    def _processLYRIC(self, text):
        self.parseMode = ParseMode.INLYRIC
        line = Line(LineType.LYRIC, text)
        self.currentTrack.addLine(line)

        return self.error

    def _processINLYRIC(self, line):
        outval = OutVal()

        # check for blank
        if len(line) == 0:
            self.parseMode = ParseMode.INTRACK
            return self._processBLANK()
        # check for a track
        elif self.isTRACKLINE(outval, line):
            return outval.value
        # check for a subtrack
        elif self.isSUBTRACKLINE(outval, line):
            return outval.value
        # check for emote
        elif SearchConditional.search(outval, r"^\[(.*)\]$", line):
            return self._processEMOTE(outval.value.group(1))
        else:
            return self._processLYRIC(line)

    def _setError(self, msg, lineNo, line):
        self.error = True
        self.errorMsg = msg
        self.errorLineNo = lineNo
        self.errorLine = line

    def _processLine(self, line):

        if self.parseMode == ParseMode.BEGIN:
            return self._processBEGIN(line)
        elif self.parseMode == ParseMode.INTRACK:
            return self._processINTRACK(line)
        elif self.parseMode == ParseMode.INSCENE:
            return self._processINSCENE(line)
        elif self.parseMode == ParseMode.INLYRIC:
            return self._processINLYRIC(line)

class LibrettoPrinter:
    def __init__(self):
        self.totalTime = datetime.timedelta()

    def print(self, libretto):
        self.totalTime = datetime.timedelta()

        for t in libretto.tracks:
            self.printTrack(t)

        for t in libretto.tracks:
            print(f"Track {t.trackNo}, ({t.length})")
        print(f"Tracks: {len(libretto.tracks)}")
        print(f"Total time: {self.totalTime}")

    def printTrack(self, track):
        if track.parent is None:
            print(f"Track {track.trackNo}, ({track.length})")
            self.totalTime += track.length
        else:
            print(f"Subtrack {track.trackNo}, ({track.length})")

        for l in track.lines:
            typeStr = LineType.toStr(l.type)

            if l.text is None:
                print(f"[{typeStr}]")
            elif l.subtext is None:
                print(f"[{typeStr}] {l.text}")
            else:
                print(f"[{typeStr}] {l.text} [{l.subtext}]")

        for t in track.subtracks:
            self.printTrack(t)

class Libretto:
    def __init__(self, tracks):
        self.tracks = tracks

def usage():
    print(f"usage: {BIN} <libretto_file>")

def main(argv):
    if len(argv) < 1:
        usage()
        return 1

    file = argv[0]
    loader = LibrettoLoader()
    libretto = loader.load(file)

    if loader.error:
        print(f"Error at line {loader.errorLineNo}[{loader.errorMsg}]:{loader.errorLine}")

    printer = LibrettoPrinter()
    printer.print(libretto)

    return 0

if __name__ == '__main__':
    import sys, os
    #breakpoint()
    BIN = os.path.basename(sys.argv[0])
    sys.exit(main(sys.argv[1:]))
