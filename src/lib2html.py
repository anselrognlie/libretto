# pylint: disable=missing-module-docstring, too-many-lines

import datetime
import sys
import os
import re

from src.libretto import LibrettoLoader
from src.libretto import LineType
from src.libretto import Track

BIN=None

class SideBySideMode:
    # pylint: disable=missing-class-docstring, too-few-public-methods
    NONE = 0
    START =1
    END = 2
    MIDDLE = 3

class Duration:
    # pylint: disable=missing-class-docstring, too-few-public-methods
    def __init__(self):
        self.hour = 0
        self.min = 0
        self.sec = 0

    @classmethod
    def from_time_delta(cls, delta):
        # pylint: disable=missing-function-docstring
        dur = Duration()

        dur.sec = int(delta) % 60
        minute = int(delta / 60)
        dur.min = minute % 60
        dur.hour = int(minute / 60)

        return dur

class Libretto2Html:
    # pylint: disable=missing-class-docstring
    def __init__(self, source_file_name):
        self.line_printer_table = {
            LineType.SCENE: self.print_scene,
            LineType.SDETAILS: self.print_sdetails,
            LineType.STAGING: self.print_staging,
            LineType.CHARACTER: self.print_character,
            LineType.LYRIC: self.print_lyric,
            LineType.EMOTE: self.print_emote,
            LineType.BLANK: self.print_blank,
        }

        self.line_queue = None
        self.sbs_mode = SideBySideMode.NONE
        self.lines_since_blank = 9999
        self.source_file_name = source_file_name

    def print_scene(self, line):
        # pylint: disable=missing-function-docstring, no-self-use
        print(f"<h1>{line.text}</h1>")

    def print_sdetails(self, line):
        # pylint: disable=missing-function-docstring, no-self-use
        print(f"<h2>{line.text}</h2>")

    def print_blank(self, _line):
        # pylint: disable=missing-function-docstring, no-self-use
        print("<p class='blank'></p>")

    def print_staging(self, line):
        # pylint: disable=missing-function-docstring, no-self-use
        print(f"<p class='staging'>{line.text}</p>")

    def print_character(self, line):
        # pylint: disable=missing-function-docstring, no-self-use
        subtext = line.subtext
        if subtext is not None:
            subtext = re.sub(r"^with above(, )?", "", subtext)
            if subtext == "":
                subtext = None

        if subtext is not None:
            print(f"""<p><span class='character'>{line.text}:</span>
                         <span class='emote'>[{subtext}]</span>
                      </p>""")
        else:
            print(f"<p class='character'>{line.text}:</p>")

    def print_lyric(self, line):
        # pylint: disable=missing-function-docstring, no-self-use
        print(f"<p class='lyric'>{line.text}</p>")

    def print_emote(self, line):
        # pylint: disable=missing-function-docstring, no-self-use
        print(f"<p class='emote'>[{line.text}]</p>")

    def print_generic(self, line):
        # pylint: disable=missing-function-docstring, no-self-use
        print(f"<p>{line.text}</p>")

    def get_side_by_side_mode(self, line):
        # pylint: disable=missing-function-docstring, no-self-use
        if (line.subtext is not None and
            re.search(r"^with above", line.subtext) is not None):
            return SideBySideMode.END

        return SideBySideMode.NONE

    def emit_queue(self):
        # pylint: disable=missing-function-docstring
        if self.line_queue is not None:
            self.print_lines(self.line_queue)

        self.line_queue = None

        # if we just emitted the start of a sbs, switch mode to end
        # otherwise, the mode should become none

        if (self.sbs_mode == SideBySideMode.START or
            self.sbs_mode == SideBySideMode.MIDDLE):
            self.sbs_mode = SideBySideMode.END
        else:
            self.sbs_mode = SideBySideMode.NONE

    def print_lines(self, lines):
        # pylint: disable=missing-function-docstring
        if self.sbs_mode == SideBySideMode.START:
            print("""
                <div class="side-by-side">
                <div>
            """)
        elif self.sbs_mode == SideBySideMode.MIDDLE:
            print("<div>")
        elif self.sbs_mode == SideBySideMode.END:
            print("<div>")

        for line in lines:
            self.print_line(line)

        if self.sbs_mode == SideBySideMode.START:
            print("</div>")
        elif self.sbs_mode == SideBySideMode.MIDDLE:
            print("</div>")
        elif self.sbs_mode == SideBySideMode.END:
            print("""
                </div>
                </div>
            """)

    def enqueue_line(self, line):
        # pylint: disable=missing-function-docstring
        if self.line_queue is None:
            self.line_queue = []

        self.line_queue.append(line)

    def print_line(self, line):
        # pylint: disable=missing-function-docstring
        printer = self.line_printer_table.get(line.type, self.print_generic)
        printer(line)

    def halts_queue(self, line_type):
        # pylint: disable=missing-function-docstring, no-self-use
        return line_type in (LineType.STAGING, LineType.SDETAILS, LineType.SCENE)

    def generate_track_details(self, info, track):
        # pylint: disable=missing-function-docstring, no-self-use
        time = track.length
        track_id = track.track_number
        dur = Duration.from_time_delta(time.seconds)
        info.append(f"""new TrackInfo("{track_id}", """ +
            f"new Duration({dur.hour}, {dur.min}, {dur.sec})),")

    def generate_div_details(self, info, track):
        # pylint: disable=missing-function-docstring, no-self-use
        time = track.length
        total_seconds = time.seconds

        # reinterpret durations as start times
        track_and_subtracks = [ Track(track.track_number) ]
        for subtrack in track.subtracks:
            track_and_subtracks.append(Track(subtrack.track_number,
                seconds=subtrack.length.seconds))

        # determine durations of track entry points
        for i in range(len(track_and_subtracks) - 1):
            current_track = track_and_subtracks[i]
            current_start = current_track.length.seconds
            track_id = current_track.track_number
            next_track = track_and_subtracks[i + 1]
            next_start = next_track.length.seconds
            seconds_delta = next_start - current_start
            total_seconds -= seconds_delta
            dur = Duration.from_time_delta(seconds_delta)

            info.append(f"""new TrackInfo("{track_id}", """ +
                f"new Duration({dur.hour}, {dur.min}, {dur.sec})),")

        # this is the last track, so use whatever time is left for this track
        current_track = track_and_subtracks[len(track_and_subtracks) - 1]
        track_id = current_track.track_number
        dur = Duration.from_time_delta(total_seconds)
        info.append(f"""new TrackInfo("{track_id}", """ +
            f"new Duration({dur.hour}, {dur.min}, {dur.sec})),")

    def print(self, libretto):
        # pylint: disable=missing-function-docstring
        total_time = datetime.timedelta()

        # generate the track info to inject into the template
        track_info = []
        for track in libretto.tracks:
            self.generate_track_details(track_info, track)

        info_str = "\n".join(track_info)

        div_info = []
        for track in libretto.tracks:
            self.generate_div_details(div_info, track)

        div_info_str = "\n".join(div_info)

        print("<html><head>")
        print(f"""
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<script type="text/javascript">
<!--

var scrollBuffer = 0;
var body = null;
var libretto = null;
var buffers = null;
var transport = null;

function ArrayUtil() {{
}}

ArrayUtil.binaryIndexSearch = function(array, value, searchOp) {{
    var len = array.length;

    var left = 0;
    var right = len;

    while (left < right) {{
        var idx = Math.floor((right - left) / 2) + left;
        var el = array[idx];

        var cmp = searchOp(value, el);
        if (cmp == 0) {{
            return idx;
        }}
        if (cmp < 0) {{
            // value was below the checked element, so we need to look to the left
            right = idx;
        }}
        else {{
            left = idx + 1;
        }}
    }}

    // not found
    return -1;
}}

ArrayUtil.binarySearch = function(array, value, searchOp) {{
    var idx = ArrayUtil.binaryIndexSearch(array, value, searchOp);
    if (idx == -1) {{
        return null;
    }}

    return array[idx];
}}

function Duration(hh, mm, ss) {{
    this.hour = hh;
    this.min = mm;
    this.sec = ss;
}}

Duration.prototype = {{
    constructor: Duration,

    copy: function() {{
        return new Duration(this.hour, this.min, this.sec);
    }},

    toTicks: function() {{
        var ticks = this.sec + this.min * 60 + this.hour * 60 * 60;
        return ticks;
    }},
}};

Duration.zero = function() {{
    return new Duration(0, 0, 0);
}}

Duration.sum = function(d1, d2) {{
    sec = d1.sec + d2.sec;

    min = Math.floor(sec / 60);
    sec = Math.floor(sec) % 60;
    min = min + d1.min + d2.min;
    hour = Math.floor(min /60);
    min = Math.floor(min) % 60;

    return new Duration(hour, min, sec);
}}

Duration.fromTicks = function(ticks) {{
    var sec = Math.floor(ticks) % 60;
    var time = Math.floor(ticks / 60);
    var min = time % 60;
    var hour = Math.floor(time / 60);

    return new Duration(hour, min, sec);
}}

Duration.compare = function(d1, d2) {{
    // returns 0 if equal, -1 if d1 is LOWER, and 1 if d2 is LOWER

    if (d1.hour < d2.hour) {{ return -1; }}
    else if (d2.hour < d1.hour) {{ return 1; }}

    if (d1.min < d2.min) {{ return -1; }}
    else if (d2.min < d1.min) {{ return 1; }}

    if (d1.sec < d2.sec) {{ return -1; }}
    else if (d2.sec < d1.sec) {{ return 1; }}
    else {{ return 0; }}
}}

function TrackInfo(id, duration) {{
    this.id = id;
    this.duration = duration;
    this.offsetHeight = 0;
    this.startTicks = 0;
    this.endTicks = 0;
    this.cumulativeHeight = 0;
}}

function Transport() {{
        this.transport = null;
        this.controls = null;
        this.ticks = 0;
        this.track = "1"
        this.tracks = { len(libretto.tracks) };
        this.keyPrefix = "{ self.source_file_name }";
        this.playTimer = null;
        this.trackTotal = null;
        this.ticksTotal = 0;
        this.targetOffset = 0;
        this.currentOffset = 0;
        this.lyricTimer = null;
        this.divCache = null;
        this.targetTrack = null;
        this.supressSliderRefresh = false;
        this.dragEndHandler = null;
        this.dragHandler = null;
        this.sliderWidth = 100;
        this.sliderLeft = 0;
        this.shouldHide = false;
        this.wakelock = null;
        this.lockRequest = null;
        this.shouldLock = false;
        this.fullscreen = false;
        this.cursorTimeout = 3000;
        this.events = {{}};

        this.trackList = [
        { info_str }
        ];

        this.allDivs = [
        { div_info_str }
        ];

        trackTotal = new Duration(0, 0, 0);
        for (var i = 0; i < this.trackList.length; ++i) {{
            trackTotal = Duration.sum(trackTotal, this.trackList[i].duration);
        }}

        this.trackTotal = trackTotal;
        this.ticksTotal = trackTotal.toTicks();
        //console.log(trackTotal);

        this.init();
    }}

Transport.prototype = {{
    constructor: Transport,

    init: function() {{
        var self = this;

        this.body = document.getElementsByTagName("body")[0];
        this.transportEl = document.getElementById("transport");
        this.controlsEl = this.transportEl.getElementsByClassName("controls")[0];
        this.playEl = this.transportEl.getElementsByClassName("play")[0];
        this.pauseEl = this.transportEl.getElementsByClassName("pause")[0];
        this.prevEl = this.transportEl.getElementsByClassName("prev")[0];
        this.nextEl = this.transportEl.getElementsByClassName("next")[0];
        this.trackEl = this.transportEl.getElementsByClassName("track")[0];
        this.tracksEl = this.transportEl.getElementsByClassName("tracks")[0];
        this.timeEl = this.transportEl.getElementsByClassName("time")[0];
        this.totalTimeEl = this.transportEl.getElementsByClassName("totalTime")[0];
        this.navEl = this.transportEl.getElementsByClassName("nav")[0];
        this.statusEl = this.transportEl.getElementsByClassName("status")[0];
        this.sliderEl = this.transportEl.getElementsByClassName("slider")[0];
        this.sliderTrackEl = this.transportEl.getElementsByClassName("sliderTrack")[0];

        this.initWakeLock();

        this.transportEl.addEventListener("mouseover", function(event) {{
            return self.onTransportOver(event);
        }});
        this.transportEl.addEventListener("mouseleave", function(event) {{
            return self.onTransportExit(event);
        }});
        this.playEl.addEventListener("click", function(event) {{
            self.play();
        }});
        this.pauseEl.addEventListener("click", function(event) {{
            self.pause();
        }});
        this.prevEl.addEventListener("click", function(event) {{
            self.previousTrack();
        }});
        this.nextEl.addEventListener("click", function(event) {{
            self.nextTrack();
        }});
        this.sliderEl.addEventListener("mousedown", function(event) {{
            self.beginSliderDrag();
        }});

        document.addEventListener("keypress", function(event) {{
            self.handleKeyPress(event);
        }});
        document.addEventListener("keyup", function(event) {{
            self.handleKeyUp(event);
        }});
        document.addEventListener("mousemove", function(event) {{
            self.resetCursor();
        }});

        this.reloadTicks();
        this.resetCursor();

        this.render();
    }},

    initWakeLock: function() {{
        self = this;
        onerror = () => {{
            console.log("init wakelock failed");
            self.body.style.cursor = "not-allowed";
        }}

        if (navigator.getWakeLock) {{
            navigator.getWakeLock("screen").then((wlObj) => {{
                self.wakelock = wlObj;

                console.log("init wakelock");

                if (self.shouldLock) {{
                    self.getNewLockRequest();
                }}
            }})
            .catch(e => onerror());
        }} else {{
            onerror();
        }}
    }},

    reloadTicks: function() {{
        var ticks = this.getCookie("ticks");
        if (ticks) {{
            this.setTicks(parseFloat(ticks));
            this.updateTrackFromTicks();
        }}
    }},

    resetCursor: function() {{
        //console.log("resetCursor");
        document.documentElement.style.cursor = "auto";

        if (this.hideCursorTimer) {{
            window.clearTimeout(this.hideCursorTimer);
        }}

        self = this;
        this.hideCursorTimer = window.setTimeout(function() {{
            self.hideCursor();
        }}, this.cursorTimeout);
    }},

    hideCursor: function() {{
        //console.log("hideCursor");
        if (this.hideCursorTimer) {{
            window.clearTimeout(this.hideCursorTimer);
        }}

        this.hideCursorTimer = 0;
        document.documentElement.style.cursor = "none";
    }},

    handleKeyUp: function(event) {{
        if (! event) {{
            event = window.event;
        }}

        if (event.keyCode == 27) {{
            this.cancelFullscreen();
        }}
    }},

    handleKeyPress: function(event) {{
        if (! event) {{
            event = window.event;
        }}

        var key = event.key;
        //console.log(key);
        //console.log(event.keyCode);

        if (key == "-") {{
            this.tick(-1);
        }}
        else if (key == "=") {{
            this.tick(1);
        }}
        else if (key == " " || key == "k") {{
            if (! this.playTimer) {{
                this.play();
            }}
            else {{
                this.pause();
            }}
        }}
        else if (key == "[") {{
            this.previousTrack();
        }}
        else if (key == "]") {{
            this.nextTrack();
        }}
        else if (key == "0") {{
            this.setTrack("1");
        }}
        else if (key == "f") {{
            this.toggleFullscreen();
        }}
    }},

    cancelFullscreen: function() {{
        document.webkitExitFullscreen();
        this.fullscreen = false;

        this.notifyResized();
    }},

    toggleFullscreen: function() {{
        this.fullscreen = ! this.fullscreen;
        if (this.fullscreen) {{
            document.documentElement.webkitRequestFullscreen();
            this.notifyResized();
        }}
        else {{
            this.cancelFullscreen();
        }}
    }},

    notifyResized: function() {{
        var map = this.events.resize;
        if (map) {{
            for (var id in map.events) {{
                map.events[id]();
            }}
        }}
    }},

    addEventListener: function(event, callback) {{
        // get the event map
        var map = this.events[event];
        if (! map) {{
            map = {{ id: 0, events: {{}} }};
            this.events[event] = map;
        }}

        id = ++map.id;
        map[id] = callback;

        return id;
    }},

    removeEventListener: function(event, id) {{
        // get the event map
        var map = this.events[event];
        if (map) {{
            delete map[id];
        }}
    }},

    beginSliderDrag: function(event) {{
        // stop any playback
        this.pause();

        // prevent the ui from updating the slider while we're moving it
        this.supressSliderRefresh = true;
        console.log("start drag");

        self = this;

        this.dragEndHandler = function(event) {{
            self.endSliderDrag();
        }};

        this.dragHandler = function(event) {{
            self.updateSliderDrag();
        }};

        document.addEventListener("mouseup", this.dragEndHandler);
        document.addEventListener("mousemove", this.dragHandler);
    }},

    endSliderDrag: function(event) {{
        document.removeEventListener("mouseup", this.dragEndHandler);
        document.removeEventListener("mousemove", this.dragHandler);

        this.dragEndHandler = null;
        this.dragHandler = null;

        this.supressSliderRefresh = false;
        console.log("end drag");

        // if we were waiting to hide the transport. do it now
        if (this.shouldHide) {{
            this.hideControls();
        }}
    }},

    updateSliderDrag: function(event) {{
        if (! event) {{
            event = window.event;
        }}

        // update the slider from the x position, clamped to either end
        mouseX = event.clientX;

        trackLeft = this.sliderLeft
        trackRight = trackLeft + this.sliderWidth;

        if (mouseX < trackLeft) {{ mouseX = trackLeft; }}
        if (mouseX > trackRight) {{ mouseX = trackRight; }}

        this.sliderEl.style.left = mouseX + "px";

        // update ticks and display from current slider position
        var percentage = this.getSliderPercent(mouseX);
        this.setTicks(this.ticksTotal * percentage);

        // may need to update track from accumulated ticks
        this.updateTrackFromTicks();

        this.render();
    }},

    getSliderPercent: function(sliderPosition) {{
        trackLeft = this.sliderLeft;
        trackWidth = this.sliderWidth;

        var sliderLeft = sliderPosition;

        var percent = (sliderLeft - trackLeft) / trackWidth;
        if (percent < 0) {{ percent = 0; }}
        if (percent > 1) {{ percent = 1; }}

        return percent;
    }},

    onTransportOver: function(event) {{
        this.controlsEl.style.display = "block";
        this.refreshSlider();
        this.shouldHide = false;
    }},

    onTransportExit: function(event) {{
        // if not dragging slider, hide
        if (! this.supressSliderRefresh) {{
            this.hideControls();
        }}
        this.shouldHide = true;
    }},

    hideControls: function() {{
        this.controlsEl.style.display = "none";
    }},

    render: function() {{
        this.trackEl.innerHTML = this.format2Digits(this.track);
        this.tracksEl.innerHTML = this.format2Digits(this.tracks);
        this.timeEl.innerHTML = this.formatInterval(this.ticks);
        //console.log(this.ticksTotal);
        this.totalTimeEl.innerHTML = this.formatInterval(this.ticksTotal);

        this.refreshSlider();

        this.startLyricTimer();
    }},

    startLyricTimer: function() {{
        if (!this.lyricTimer) {{
            var self = this;
            this.lyricTimer = window.setInterval(function() {{
                self.updateLyrics();
            }}, 16);
        }}
    }},

    stopLyricTimer: function() {{
        if (this.lyricTimer) {{
            window.clearInterval(this.lyricTimer);
            this.lyricTimer = null;
        }}
    }},

    refreshTrackHeights: function() {{
        var startTicks = 0;
        var endTicks = 0;
        var cumulativeHeight = 0;

        for (var i = 0; i < this.allDivs.length; ++i)
        {{
            var track = this.allDivs[i];
            var id = track.id;

            var trackEl = document.getElementById(id.toString());
            track.offsetHeight = trackEl.offsetHeight;

            // update cache fields
            endTicks = startTicks + track.duration.toTicks();
            track.startTicks = startTicks;
            track.endTicks = endTicks;
            track.cumulativeHeight = cumulativeHeight;

            startTicks = endTicks;
            cumulativeHeight += track.offsetHeight;

            //console.log(track);
        }}
    }},

    updateLyrics: function() {{
        this.updateTargetOffset();
        this.updateCurrentOffset();

        // if the current offset is within 1px of the target, just jump to
        // the location, and stop updating

        if (Math.abs(this.currentOffset - this.targetOffset) < 1) {{
            this.currentOffset = this.targetOffset;
            this.stopLyricTimer();
        }}

        this.applyOffsetToMarkup();
    }},

    updateTargetOffset: function() {{
        // are we still in the right target track?
        var track = this.targetTrack;

        // only lookup a new track if we've moved outside the bounds
        if (track == null || this.ticks < track.startTicks ||
            this.ticks > track.endTicks) {{

            track = ArrayUtil.binarySearch(this.allDivs, this.ticks,
                function(a, b) {{
                    if (a < b.startTicks) {{ return -1; }}
                    else if (a >= b.endTicks) {{ return 1; }}
                    else {{ return 0; }}
                }});

            if (track == null) {{
                track = this.allDivs[this.allDivs.length - 1];
            }}

            this.targetTrack = track;
        }}

        var wholeTrackTicks = track.startTicks;
        var wholeTrackHeights = track.cumulativeHeight;

        // get the offsets up to the current track, then add on the partial
        var tickRemainder = this.ticks - wholeTrackTicks;
        var tickPercent = tickRemainder / track.duration.toTicks();

        // offset for the current track
        var partialHeight = track.offsetHeight * tickPercent;
        var offsetHeight = wholeTrackHeights + partialHeight;

        this.targetOffset = offsetHeight;
    }},

    updateCurrentOffset: function() {{
        var dist = this.targetOffset - this.currentOffset;
        var delta = dist / 10;
        this.currentOffset += delta;
    }},

    applyOffsetToMarkup: function() {{
        var body = document.getElementsByTagName("body")[0];
        body.scrollTop = this.currentOffset;
    }},

    format2Digits: function(value) {{
        if (value > 9) {{
            return value.toString();
        }}
        else
        {{
            return "0" + value.toString();
        }}
    }},

    formatInterval: function(interval) {{
        var sec = Math.floor(interval) % 60;
        var time = Math.floor(interval / 60);
        var min = time % 60;
        var hour = Math.floor(time / 60);

        var hourStr = null;
        if (hour > 0) {{
            hourStr = hour.toString();
        }}

        var minStr = null;
        if (hourStr) {{
            minStr = min.toString();
        }}
        else
        {{
            minStr = this.format2Digits(min);
        }}

        var secStr = this.format2Digits(sec);

        if (hourStr) {{
            return hourStr + ":" + minStr + ":" + secStr;
        }}
        else {{
            return minStr + ":" + secStr;
        }}
    }},

    getNewLockRequest: function() {{
        if (this.wakelock) {{
            var oldLockRequest = this.lockRequest;
            this.lockRequest = null;
            if (oldLockRequest) {{
                oldLockRequest.cancel();
            }}

            this.lockRequest = this.wakelock.createRequest();
            console.log("wakelock");
        }}
    }},

    cancelLockRequest: function() {{
        if (this.lockRequest) {{
            var lockRequest = this.lockRequest;
            this.lockRequest = null;
            lockRequest.cancel();
            console.log("cancel wakelock");
        }}
    }},

    play: function() {{
        var self = this;

        console.log("play");
        if (! this.playTimer) {{

            self.shouldLock = true;
            self.getNewLockRequest();

            this.playTimer = window.setInterval(function(){{
                self.tick(.1);
            }}, 100);
        }}
    }},

    pause: function() {{
        console.log("pause");
        if (this.playTimer) {{

            this.cancelLockRequest();
            this.shouldLock = false;

            window.clearInterval(this.playTimer);
            this.playTimer = null;
        }}
    }},

    updateTrackFromTicks: function() {{
        var current = Duration.fromTicks(this.ticks);

        if (Duration.compare(current, this.trackTotal) == 1) {{
            current = this.trackTotal.copy();
        }}

        // advance through tracks until we find a total duration exceeding
        // the duration

        var total = Duration.zero();
        var i = 0;
        var info = null;
        var tracks = this.trackList.length;
        do {{
            info = this.trackList[i++];
            total = Duration.sum(total, info.duration);
        }} while (i < tracks && Duration.compare(total, current) <= 0);

        // info contains the track containing the current duration
        this.track = info.id;
    }},

    tick: function(ticks) {{

        this.setTicks(this.ticks + ticks);

        // may need to update track from accumulated ticks
        this.updateTrackFromTicks();

        this.render();
    }},

    setTicks: function(ticks) {{
        var newTicks = ticks;

        //console.log("ticks: " + this.ticks);
        //console.log("ticksTotal: " + this.ticksTotal);

        if (newTicks > this.ticksTotal) {{
            newTicks = this.ticksTotal;
            this.pause();
        }}

        if (newTicks < 0) {{
            newTicks = 0;
            this.pause();
        }}

        this.ticks = newTicks;
        this.setCookie("ticks", this.ticks);
    }},

    setCookie: function(key, value) {{
        window.localStorage.setItem(this.keyPrefix + "." + key, value);
    }},

    getCookie: function(key) {{
        return window.localStorage.getItem(this.keyPrefix + "." + key);
    }},

    updateTicksFromTrack: function() {{
        var duration = Duration.zero();

        var currIdx = this.findIdxFromId(this.track);

        // sum duration up to previous track, then get the ticks
        for (var i = 0; i < currIdx; ++i) {{
            duration = Duration.sum(duration, this.trackList[i].duration);
        }}

        this.setTicks(duration.toTicks());
    }},

    previousTrack: function() {{
        this.pause();

        var currIdx = this.findIdxFromId(this.track);

        if (currIdx > 0 ) {{
            this.track = this.trackList[currIdx - 1].id;

            this.updateTicksFromTrack();

            this.render();
        }}
    }},

    nextTrack: function() {{
        this.pause();

        var maxTrackIdx = this.trackList.length - 1;
        var currIdx = this.findIdxFromId(this.track);
        if (currIdx < maxTrackIdx ) {{
            this.track = this.trackList[currIdx + 1].id;

            this.updateTicksFromTrack();

            this.render();
        }}
    }},

    setTrack: function(id) {{
        this.track = id;
        this.updateTicksFromTrack();
        this.render();
    }},

    findIdxFromId: function(id) {{
        var idx = 0;
        for ( ; idx < this.trackList.length; ++idx) {{
            if (this.trackList[idx].id == id) {{
                break;
            }}
        }}

        return idx;
    }},

    onResize: function() {{
        transport.refreshTrackHeights();
        this.render();
    }},

    refreshSlider: function() {{
        if (this.supressSliderRefresh) {{
            return;
        }}

        // width should be the total width less the two transport floats
        // and the left position should be the left float width

        var totalWidth = this.controlsEl.offsetWidth;
        var leftWidth = this.navEl.offsetWidth;
        var rightWidth = this.statusEl.offsetWidth;

        var sliderWidth = (totalWidth - (leftWidth + rightWidth));
        var sliderLeft = leftWidth;

        var sliderTrack = this.sliderTrackEl;
        sliderTrack.style.width = sliderWidth + "px";
        sliderTrack.style.left = sliderLeft + "px";

        // get shuttle position along length as percentage of time
        var percentTime = this.ticks / this.ticksTotal;
        var shuttleLeft = percentTime * sliderWidth + sliderLeft;
        this.sliderEl.style.left = shuttleLeft + "px";

        // cache slider sizes for ui calculations
        this.sliderWidth = sliderWidth;
        this.sliderLeft = sliderLeft;
    }},

}};

function onLoad(event) {{
    body = document.getElementsByTagName("body")[0];
    window.addEventListener("resize", onResize);
    libretto = document.getElementsByClassName("libretto");
    buffers = document.getElementsByClassName("scroll-buffer");
    //console.log(buffers.length);

    transport = new Transport();
    transport.addEventListener("resize", onResize);

    onResize();

    //testArraySearch();
}}

function onResize() {{
    //console.log("global onresize");
    updateBuffers();
    transport.onResize();
}}

function updateBuffers() {{
    scrollBuffer = body.clientHeight / 2;
    console.log("scrollBuffer: " + scrollBuffer);
    for (var i = 0; i < buffers.length; ++i) {{
        b = buffers[i];
        b.style.height = scrollBuffer + "px";
    }}
}}

-->
</script>

                <style type="text/css">
                    * {{
                        margin: 0;
                        padding: 0;
                    }}

                    body {{
                        background-color: black;
                        color: white;
                        font-size: 28pt;
                        font-family: Helvetica;
                        overflow: hidden;
                    }}

                    h1, h2 {{
                        font-size: 1em;
                    }}

                    p, h1, h2 {{
                        line-height: 1.25em;
                    }}

                    p {{
                        padding-left: 1em;
                        text-indent: -1em;
                    }}

                    .libretto {{
                        padding-left: .25em;
                    }}

                    .staging {{
                        margin-bottom: 1em;
                        padding-left: 0;
                        text-indent: 0;
                        font-size: .75em;
                        font-weight: 200;
                        color: gray;
                    }}

                    .character {{
                        font-weight: 800;
                    }}

                    .blank {{
                        margin-bottom: 1em;
                    }}

                    .emote {{
                        font-size: .75em;
                        font-weight: 200;
                        font-style: italic;
                        color: gray;
                    }}

                    .lyric {{
                        font-weight: 200;
                        font-size: .9em;
                    }}

                    .libretto .track {{
                        border: solid 1px black;
                    }}

                    /* rules for side-by-side */
                    .side-by-side {{
                        display: flex;
                        margin-bottom: 1em;
                    }}

                    .side-by-side > div {{
                        padding-right: 1em;
                        align-content: space-between;
                    }}

                    .side-by-side div p:last-child {{
                        margin-bottom: 0;
                    }}

                    /* transport styles */
                    #transport {{
                        position: fixed;
                        height: 1em;
                        width: 100%;
                        user-select: none;
                    }}

                    #transport .controls {{
                        position: relative;
                        height: 2em;
                        font-size: .5em;
                        text-align: right;
                        display: none;
                        background-color: white;
                        color: black;
                        line-height: 2em;
                        text-transform: uppercase;
                    }}

                    #transport a {{
                        text-decoration: none;
                        padding-right: .5em;
                    }}

                    #transport a:hover {{
                        cursor: default;
                    }}

                    #transport .nav {{
                        float: left;
                        padding: 0 .5em;
                    }}

                    #transport .status {{
                        float: right;
                        padding: 0 1em;
                    }}

                    #transport .sliderTrack {{
                        display: block;
                        position: absolute;
                        height: 2px;
                        top: 1em;
                        margin-top: -1px;
                        left: 0;
                        overflow: hidden;
                        background-color: black;
                    }}

                    #transport .slider {{
                        display: block;
                        position: absolute;
                        height: 1em;
                        top: .5em;
                        left: 0;
                        width: .5em;
                        margin-left: -.25em;
                        overflow: hidden;
                        background-color: gray;
                    }}

                    #transport .spacing {{
                        visibility: hidden;
                    }}

                    #top-fade {{
                        position: fixed;
                        width: 100%;
                        height: 52px;
                        background-image: url(data:image/png;base64,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Imh0dHA6Ly9wdXJsLm9yZy9kYy9lbGVtZW50cy8xLjEvIgogICAgeG1sbnM6ZXhpZj0iaHR0cDovL25zLmFkb2JlLmNvbS9leGlmLzEuMC8iCiAgICB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iCiAgIHhtcE1NOkRvY3VtZW50SUQ9ImdpbXA6ZG9jaWQ6Z2ltcDoxMGIyNjljZS02ZTc0LTQ4YzMtYmU1Ny00ZjBjNTIxZmMzYzgiCiAgIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6ZGMxYjY2NzYtNjZkYi00NzMwLTllNTYtNmQ3M2ZkZGQ4NDNlIgogICB4bXBNTTpPcmlnaW5hbERvY3VtZW50SUQ9InhtcC5kaWQ6YzcyODVhNGMtYmExNC00MmEyLWFkYWMtNTMyOTI1ZDI1OGE1IgogICBHSU1QOkFQST0iMi4wIgogICBHSU1QOlBsYXRmb3JtPSJNYWMgT1MiCiAgIEdJTVA6VGltZVN0YW1wPSIxNTU2Mjg4NTMwODQxNzM4IgogICBHSU1QOlZlcnNpb249IjIuMTAuOCIKICAgZGM6Rm9ybWF0PSJpbWFnZS9wbmciCiAgIGV4aWY6UGl4ZWxYRGltZW5zaW9uPSI4NTAiCiAgIGV4aWY6UGl4ZWxZRGltZW5zaW9uPSI4MTQiCiAgIHhtcDpDcmVhdG9yVG9vbD0iR0lNUCAyLjEwIj4KICAgPGlwdGNFeHQ6TG9jYXRpb25DcmVhdGVkPgogICAgPHJkZjpCYWcvPgogICA8L2lwdGNFeHQ6TG9jYXRpb25DcmVhdGVkPgogICA8aXB0Y0V4dDpMb2NhdGlvblNob3duPgogICAgPHJkZjpCYWcvPgogICA8L2lwdGNFeHQ6TG9jYXRpb25TaG93bj4KICAgPGlwdGNFeHQ6QXJ0d29ya09yT2JqZWN0PgogICAgPHJkZjpCYWcvPgogICA8L2lwdGNFeHQ6QXJ0d29ya09yT2JqZWN0PgogICA8aXB0Y0V4dDpSZWdpc3RyeUlkPgogICAgPHJkZjpCYWcvPgogICA8L2lwdGNFeHQ6UmVnaXN0cnlJZD4KICAgPHhtcE1NOkhpc3Rvcnk+CiAgICA8cmRmOlNlcT4KICAgICA8cmRmOmxpCiAgICAgIHN0RXZ0OmFjdGlvbj0ic2F2ZWQiCiAgICAgIHN0RXZ0OmNoYW5nZWQ9Ii8iCiAgICAgIHN0RXZ0Omluc3RhbmNlSUQ9InhtcC5paWQ6YTllNjZiN2YtMDFmZi00YzYwLWEwNzctNmRkNTk3M2E2NDVlIgogICAgICBzdEV2dDpzb2Z0d2FyZUFnZW50PSJHaW1wIDIuMTAgKE1hYyBPUykiCiAgICAgIHN0RXZ0OndoZW49IjIwMTktMDQtMjZUMDc6MjI6MTAtMDc6MDAiLz4KICAgIDwvcmRmOlNlcT4KICAgPC94bXBNTTpIaXN0b3J5PgogICA8cGx1czpJbWFnZVN1cHBsaWVyPgogICAgPHJkZjpTZXEvPgogICA8L3BsdXM6SW1hZ2VTdXBwbGllcj4KICAgPHBsdXM6SW1hZ2VDcmVhdG9yPgogICAgPHJkZjpTZXEvPgogICA8L3BsdXM6SW1hZ2VDcmVhdG9yPgogICA8cGx1czpDb3B5cmlnaHRPd25lcj4KICAgIDxyZGY6U2VxLz4KICAgPC9wbHVzOkNvcHlyaWdodE93bmVyPgogICA8cGx1czpMaWNlbnNvcj4KICAgIDxyZGY6U2VxLz4KICAgPC9wbHVzOkxpY2Vuc29yPgogIDwvcmRmOkRlc2NyaXB0aW9uPgogPC9yZGY6UkRGPgo8L3g6eG1wbWV0YT4KICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgIAo8P3hwYWNrZXQgZW5kPSJ3Ij8+cAu/FAAAAAlwSFlzAAAWJQAAFiUBSVIk8AAAAAd0SU1FB+MEGg4WCmDzo3QAAABnSURBVBjTTY9BEgMxDMIk+v8HN84MPaSb9ujBIEAo6A5lBboDToSVwg50IkwKE/R7ApO2K8gToBN7bOvPQZloJ9R1vNiVcuA3tCvVfV5sJz2FfiAneIVeEI9g3emX9g4+de8Y1BcAHzu6VXGuT2W6AAAAAElFTkSuQmCC);
                        background-repeat: repeat-x;
                    }}

                    #bottom-fade {{
                        position: fixed;
                        top: 100%;
                        margin-top: -52px;
                        width: 100%;
                        height: 52px;
                        background-image: url(data:image/png;base64,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OmRjPSJodHRwOi8vcHVybC5vcmcvZGMvZWxlbWVudHMvMS4xLyIKICAgIHhtbG5zOmV4aWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20vZXhpZi8xLjAvIgogICAgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIgogICB4bXBNTTpEb2N1bWVudElEPSJnaW1wOmRvY2lkOmdpbXA6MTBiMjY5Y2UtNmU3NC00OGMzLWJlNTctNGYwYzUyMWZjM2M4IgogICB4bXBNTTpJbnN0YW5jZUlEPSJ4bXAuaWlkOmJhNTFjNTA1LTMwMzgtNDJmNS04Y2FhLTFhNDRkN2RmYmVlOCIKICAgeG1wTU06T3JpZ2luYWxEb2N1bWVudElEPSJ4bXAuZGlkOmM3Mjg1YTRjLWJhMTQtNDJhMi1hZGFjLTUzMjkyNWQyNThhNSIKICAgR0lNUDpBUEk9IjIuMCIKICAgR0lNUDpQbGF0Zm9ybT0iTWFjIE9TIgogICBHSU1QOlRpbWVTdGFtcD0iMTU1NjI5MDI2NTkxMzA4MiIKICAgR0lNUDpWZXJzaW9uPSIyLjEwLjgiCiAgIGRjOkZvcm1hdD0iaW1hZ2UvcG5nIgogICBleGlmOlBpeGVsWERpbWVuc2lvbj0iODUwIgogICBleGlmOlBpeGVsWURpbWVuc2lvbj0iODE0IgogICB4bXA6Q3JlYXRvclRvb2w9IkdJTVAgMi4xMCI+CiAgIDxpcHRjRXh0OkxvY2F0aW9uQ3JlYXRlZD4KICAgIDxyZGY6QmFnLz4KICAgPC9pcHRjRXh0OkxvY2F0aW9uQ3JlYXRlZD4KICAgPGlwdGNFeHQ6TG9jYXRpb25TaG93bj4KICAgIDxyZGY6QmFnLz4KICAgPC9pcHRjRXh0OkxvY2F0aW9uU2hvd24+CiAgIDxpcHRjRXh0OkFydHdvcmtPck9iamVjdD4KICAgIDxyZGY6QmFnLz4KICAgPC9pcHRjRXh0OkFydHdvcmtPck9iamVjdD4KICAgPGlwdGNFeHQ6UmVnaXN0cnlJZD4KICAgIDxyZGY6QmFnLz4KICAgPC9pcHRjRXh0OlJlZ2lzdHJ5SWQ+CiAgIDx4bXBNTTpIaXN0b3J5PgogICAgPHJkZjpTZXE+CiAgICAgPHJkZjpsaQogICAgICBzdEV2dDphY3Rpb249InNhdmVkIgogICAgICBzdEV2dDpjaGFuZ2VkPSIvIgogICAgICBzdEV2dDppbnN0YW5jZUlEPSJ4bXAuaWlkOmE5ZTY2YjdmLTAxZmYtNGM2MC1hMDc3LTZkZDU5NzNhNjQ1ZSIKICAgICAgc3RFdnQ6c29mdHdhcmVBZ2VudD0iR2ltcCAyLjEwIChNYWMgT1MpIgogICAgICBzdEV2dDp3aGVuPSIyMDE5LTA0LTI2VDA3OjIyOjEwLTA3OjAwIi8+CiAgICAgPHJkZjpsaQogICAgICBzdEV2dDphY3Rpb249InNhdmVkIgogICAgICBzdEV2dDpjaGFuZ2VkPSIvIgogICAgICBzdEV2dDppbnN0YW5jZUlEPSJ4bXAuaWlkOjk1ZjYzMjBlLTc5NWUtNDc0Ny05Mzk5LTA4OGVkMWEwOTdkNiIKICAgICAgc3RFdnQ6c29mdHdhcmVBZ2VudD0iR2ltcCAyLjEwIChNYWMgT1MpIgogICAgICBzdEV2dDp3aGVuPSIyMDE5LTA0LTI2VDA3OjUxOjA1LTA3OjAwIi8+CiAgICA8L3JkZjpTZXE+CiAgIDwveG1wTU06SGlzdG9yeT4KICAgPHBsdXM6SW1hZ2VTdXBwbGllcj4KICAgIDxyZGY6U2VxLz4KICAgPC9wbHVzOkltYWdlU3VwcGxpZXI+CiAgIDxwbHVzOkltYWdlQ3JlYXRvcj4KICAgIDxyZGY6U2VxLz4KICAgPC9wbHVzOkltYWdlQ3JlYXRvcj4KICAgPHBsdXM6Q29weXJpZ2h0T3duZXI+CiAgICA8cmRmOlNlcS8+CiAgIDwvcGx1czpDb3B5cmlnaHRPd25lcj4KICAgPHBsdXM6TGljZW5zb3I+CiAgICA8cmRmOlNlcS8+CiAgIDwvcGx1czpMaWNlbnNvcj4KICA8L3JkZjpEZXNjcmlwdGlvbj4KIDwvcmRmOlJERj4KPC94OnhtcG1ldGE+CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAKPD94cGFja2V0IGVuZD0idyI/Plse1x4AAAAJcEhZcwAAFiUAABYlAUlSJPAAAAAHdElNRQfjBBoOMwUYv24CAAAAaklEQVQY00WPQRICMQzDJNOU//+XGXPoFq5xLCUAoL4CnRQm4ASYUCbYd6yT2hXqnGVhUt2RzhPYCWWl3KBenu0KuB+RTORA96O0Oz0oJvSKTk3WmSH7iPR2D/TX+D8jrBT2ORxcoB+EfgHQ4ChWY5o7QwAAAABJRU5ErkJggg==);
                        background-repeat: repeat-x;
                    }}

                </style>
                </head><body onload="onLoad();">

<div id="top-fade"></div>
<div id="bottom-fade"></div>

<div id="transport">
    <div class="controls">
        <div class="nav">
<a class="play">Play</a>
<a class="pause">Pause</a>
<a class="prev">Prev</a>
<a class="next">Next</a>
</div>
<div class="sliderTrack">&nbsp;</div>
<div class="slider">&nbsp;</div>
<div class="status">
Track:
<span class="track">--</span>/<span class="tracks">--</span>
Time:
<span class="time">00:00</span>/<span class="totalTime">00:00</span>
</div>
</div>&nbsp;
</div>

<div class='libretto'>
<div class="scroll-buffer">&nbsp;</div>
                """)

        self.lines_since_blank = 9999

        for track in libretto.tracks:
            total_time += track.length
            self.print_track_lines(track)
        print("""
<div class="scroll-buffer">&nbsp;</div>
</div>

</body></html>
        """)

    def print_track_lines(self, track):
        # pylint: disable=missing-function-docstring
        print(f"<div id='{track.track_number}' class='track'>")

        for line in track.lines:
            self.lines_since_blank += 1

            line_type = line.type

            if line_type == LineType.CHARACTER:
                # emit any queued lines, using the new character line to
                # set the side by side mode
                sbs_mode = self.get_side_by_side_mode(line)
                if sbs_mode == SideBySideMode.END:
                    # the queued lines must be a side by side start
                    if self.sbs_mode == SideBySideMode.NONE:
                        self.sbs_mode = SideBySideMode.START
                    else:
                        self.sbs_mode = SideBySideMode.MIDDLE

                self.emit_queue()

                self.enqueue_line(line)
            elif line_type == LineType.BLANK:
                self.lines_since_blank = 0
                self.enqueue_line(line)
            elif line_type == LineType.EMOTE:
                # if this followed a blank, then end the queue, otherwise
                # just enqueue
                if self.lines_since_blank == 1:
                    self.emit_queue()
                self.enqueue_line(line)
            elif self.halts_queue(line_type):
                self.emit_queue()
                self.enqueue_line(line)
            else:
                self.enqueue_line(line)

        self.emit_queue()
        print("</div>")

        for subtrack in track.subtracks:
            self.print_track_lines(subtrack)

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

    printer = Libretto2Html(file)
    printer.print(libretto)

    return 0

if __name__ == '__main__':
    BIN = os.path.basename(sys.argv[0])
    sys.exit(main(sys.argv[1:]))
