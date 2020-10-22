# pylint: disable=missing-module-docstring

from __future__ import print_function
import datetime
import re
import sys
import os

BIN = None

class OutVal:
    # pylint: disable=missing-class-docstring, too-few-public-methods
    def __init__(self):
        self.value = None

class SearchConditional:
    # pylint: disable=missing-class-docstring, too-few-public-methods
    def __init__(self):
        pass

    @classmethod
    def search(cls, outval, regex, search_in):
        # pylint: disable=missing-function-docstring
        match = re.search(regex, search_in)
        outval.value = match
        return match is not None

class LineType:
    # pylint: disable=missing-class-docstring, too-few-public-methods
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
    def to_str(cls, line_type):
        # pylint: disable=missing-function-docstring
        result_str = None

        if line_type == LineType.UNKNOWN:
            result_str = "UNKNOWN"
        elif line_type == LineType.SCENE:
            result_str = "SCENE"
        elif line_type == LineType.SDETAILS:
            result_str = "SDETAILS"
        elif line_type == LineType.STAGING:
            result_str = "STAGING"
        elif line_type == LineType.CHARACTER:
            result_str = "CHARACTER"
        elif line_type == LineType.LYRIC:
            result_str = "LYRIC"
        elif line_type == LineType.EMOTE:
            result_str = "EMOTE"
        elif line_type == LineType.BLANK:
            result_str = "BLANK"

        return result_str

class ParseMode:
    # pylint: disable=missing-class-docstring, too-few-public-methods
    BEGIN = 0
    LINE = 1
    INTRACK = 2
    INSCENE = 3
    INLYRIC = 4

class Line:
    # pylint: disable=missing-class-docstring, too-few-public-methods
    def __init__(self, line_type, text=None, subtext=None):
        self.type = line_type
        self.text = text
        self.subtext = subtext

class Track:
    # pylint: disable=missing-class-docstring
    def __init__(self, track_number=0, minutes=0, seconds=0):
        self.track_number = track_number
        self.length = datetime.timedelta(minutes=minutes, seconds=seconds)
        self.lines = []
        self.subtracks = []
        self.parent = None

    def set_length(self, minutes, seconds):
        # pylint: disable=missing-function-docstring
        self.length = datetime.timedelta(minutes=minutes, seconds=seconds)

    def add_line(self, line):
        # pylint: disable=missing-function-docstring
        self.lines.append(line)

    def add_subtrack(self, track):
        # pylint: disable=missing-function-docstring
        track.parent = self
        self.subtracks.append(track)

class LibrettoLoader:
    # pylint: disable=missing-class-docstring, too-many-instance-attributes
    def __init__(self):
        self.filename = None
        self.libretto = None
        self.parse_mode = None
        self.track = 0
        self.current_track = None
        self.tracks = []
        self.error = False
        self.error_line_number = 0
        self.error_line = None
        self.error_message = None
        self.line_number = 0

    def load(self, filename):
        # pylint: disable=missing-function-docstring
        self.filename = filename
        return self._do_load()

    def _reset_parse_state(self):
        # pylint: disable=missing-function-docstring
        self.parse_mode = ParseMode.BEGIN
        self.track = 0
        self.current_track = None
        self.line_number = 0
        self.error = False

    def _do_load(self):
        # pylint: disable=missing-function-docstring
        self._reset_parse_state()

        with open(self.filename) as opened_file:
            for line in opened_file:
                self.line_number += 1

                # trim any whitespace
                line = line.strip()
                end = self._process_line(line)
                if end:
                    break

        self.libretto = Libretto(self.tracks)
        return self.libretto

    def _process_inscene(self, line):
        # if blank, this is the end of the scene
        if len(line) == 0:
            self.parse_mode = ParseMode.INTRACK
            return self._process_blank()

        self.current_track.add_line(Line(LineType.SDETAILS, line))
        return self.error


    def _process_scene(self, text):
        self.parse_mode = ParseMode.INSCENE
        line = Line(LineType.SCENE, text)
        self.current_track.add_line(line)

        return self.error

    def _process_staging(self, text):
        line = Line(LineType.STAGING, text)
        self.current_track.add_line(line)

        return self.error

    def _process_blank(self):
        line = Line(LineType.BLANK)
        self.current_track.add_line(line)

        return self.error

    def _process_character(self, name, emote=None):
        self.parse_mode = ParseMode.INLYRIC
        line = Line(LineType.CHARACTER, name, emote)
        self.current_track.add_line(line)

        return self.error

    def _process_intrack(self, line):
        outval = OutVal()
        result = None

        # is it a scene title? e.g. PROLOGUE[: blah blah]
        if SearchConditional.search(outval,
            r"^[A-Z0-9 ]+$|^[A-Z0-9 ]+:.*$", line):
            result = self._process_scene(line)

        # is it a blank line? ignore
        elif len(line) == 0:
            result = self._process_blank()

        # look for a track header e.g. [#,##:##]
        elif self.is_trackline(outval, line):
            result = outval.value

        # look for a subtrack header e.g. [##:##]
        elif self.is_subtrackline(outval, line):
            result = outval.value

        # is it a character line?  e.g. Steve: [emote]
        elif SearchConditional.search(outval, r"^([^:]+):$", line):
            match = outval.value
            result = self._process_character(match.group(1))

        elif SearchConditional.search(outval, r"^([^:]+): \[(.*)\]$", line):
            match = outval.value
            result = self._process_character(match.group(1), match.group(2))

        # does it contain emotes?  e.g. [does something]
        elif self.is_emoteline(outval, line):
            result = outval.value

        # is it flavor text?  e.g. some long text that wraps around
        elif len(line) > 40:
            result = self._process_staging(line)

        # just a regular lyric
        else:
            result = self._process_lyric(line)

        return result

    def _process_trackline(self, track, minutes, seconds, line):
        track_number = int(track)
        track = Track(track_number, int(minutes), int(seconds))
        self.track = track_number
        self.tracks.append(track)
        self.current_track = track

        # if we found the track mid lyric, stay in lyric mode
        if self.parse_mode == ParseMode.INLYRIC:
            return self._process_inlyric(line)

        self.parse_mode = ParseMode.INTRACK
        return self._process_intrack(line)

    def _process_subtrackline(self, minutes, seconds, line):
        # addd this subtrack, but if the current track is already a subtrack,
        # move up to the parent track first
        if self.current_track.parent is not None:
            self.current_track = self.current_track.parent

        subtrack_id = len(self.current_track.subtracks)
        track = Track(f"{self.current_track.track_number}.{subtrack_id}",
            int(minutes), int(seconds))

        self.current_track.add_subtrack(track)
        self.current_track = track

        # if we found the track mid lyric, stay in lyric mode
        if self.parse_mode == ParseMode.INLYRIC:
            return self._process_inlyric(line)

        self.parse_mode = ParseMode.INTRACK
        return self._process_intrack(line)

    def _process_begin(self, line):
        outval = OutVal()

        # skip a blank line
        if len(line) == 0:
            pass
        # look for a track header e.g. [#,##:##]
        elif self.is_trackline(outval, line):
            return outval.value
        else:
            # error
            self._set_error("unexpected input looking for track",
                self.line_number, line)

        return self.error

    def is_trackline(self, outval, line):
        # pylint: disable=missing-function-docstring
        match_out_value = OutVal()
        does_match = SearchConditional.search(match_out_value,
            r"^\[(\d+),(\d+):(\d+)\](.*)", line)
        if does_match:
            match = match_out_value.value
            outval.value = self._process_trackline(match.group(1),
                match.group(2), match.group(3), match.group(4).strip())

        return does_match

    def is_subtrackline(self, outval, line):
        # pylint: disable=missing-function-docstring
        match_out_value = OutVal()
        does_match = SearchConditional.search(match_out_value,
            r"^\[(\d+):(\d+)\](.*)", line)
        if does_match:
            match = match_out_value.value
            outval.value = self._process_subtrackline(match.group(1),
                match.group(2), match.group(3).strip())

        return does_match

    def is_emoteline(self, outval, line):
        # pylint: disable=missing-function-docstring
        match_out_value = OutVal()
        does_match = SearchConditional.search(match_out_value,
            r"^\[(.*)\]$", line)
        if does_match:
            match = match_out_value.value
            outval.value = self._process_emote(match.group(1))
        # make sure it wasn't malformed (multiline)
        elif SearchConditional.search(outval, r"^\[([^]]*)$", line):
            does_match = True
            self._set_error("malformed emote", self.line_number, line)
            outval.value = self.error

        return does_match

    def _process_emote(self, text):
        self.parse_mode = ParseMode.INLYRIC
        line = Line(LineType.EMOTE, text)
        self.current_track.add_line(line)

        return self.error

    def _process_lyric(self, text):
        self.parse_mode = ParseMode.INLYRIC
        line = Line(LineType.LYRIC, text)
        self.current_track.add_line(line)

        return self.error

    def _process_inlyric(self, line):
        outval = OutVal()
        result = None

        # check for blank
        if len(line) == 0:
            self.parse_mode = ParseMode.INTRACK
            result = self._process_blank()
        # check for a track
        elif self.is_trackline(outval, line):
            result = outval.value
        # check for a subtrack
        elif self.is_subtrackline(outval, line):
            result = outval.value
        # check for emote
        elif SearchConditional.search(outval, r"^\[(.*)\]$", line):
            result = self._process_emote(outval.value.group(1))
        else:
            result = self._process_lyric(line)

        return result

    def _set_error(self, msg, line_number, line):
        self.error = True
        self.error_message = msg
        self.error_line_number = line_number
        self.error_line = line

    def _process_line(self, line):
        result = None

        if self.parse_mode == ParseMode.BEGIN:
            result = self._process_begin(line)
        elif self.parse_mode == ParseMode.INTRACK:
            result = self._process_intrack(line)
        elif self.parse_mode == ParseMode.INSCENE:
            result = self._process_inscene(line)
        elif self.parse_mode == ParseMode.INLYRIC:
            result = self._process_inlyric(line)
        else:
            result = True

        return result

class LibrettoPrinter:
    # pylint: disable=missing-class-docstring
    def __init__(self):
        self.total_time = datetime.timedelta()

    def print(self, libretto):
        # pylint: disable=missing-function-docstring
        self.total_time = datetime.timedelta()

        for track in libretto.tracks:
            self.print_track(track)

        for track in libretto.tracks:
            print(f"Track {track.track_number}, ({track.length})")
        print(f"Tracks: {len(libretto.tracks)}")
        print(f"Total time: {self.total_time}")

    def print_track(self, track):
        # pylint: disable=missing-function-docstring
        if track.parent is None:
            print(f"Track {track.track_number}, ({track.length})")
            self.total_time += track.length
        else:
            print(f"Subtrack {track.track_number}, ({track.length})")

        for track_line in track.lines:
            type_str = LineType.to_str(track_line.type)

            if track_line.text is None:
                print(f"[{type_str}]")
            elif track_line.subtext is None:
                print(f"[{type_str}] {track_line.text}")
            else:
                print(f"[{type_str}] {track_line.text} [{track_line.subtext}]")

        for subtrack in track.subtracks:
            self.print_track(subtrack)

class Libretto:
    # pylint: disable=missing-class-docstring, too-few-public-methods
    def __init__(self, tracks):
        self.tracks = tracks

def usage():
    # pylint: disable=missing-function-docstring
    print(f"usage: {BIN} <libretto_file>")

def main(argv):
    # pylint: disable=missing-function-docstring
    if len(argv) < 1:
        usage()
        return 1

    file = argv[0]
    loader = LibrettoLoader()
    libretto = loader.load(file)

    if loader.error:
        print(f"Error at line {loader.error_line_number}" +
            f"[{loader.error_message}]:{loader.error_line}")

    printer = LibrettoPrinter()
    printer.print(libretto)

    return 0

if __name__ == '__main__':
    #breakpoint()
    BIN = os.path.basename(sys.argv[0])
    sys.exit(main(sys.argv[1:]))
