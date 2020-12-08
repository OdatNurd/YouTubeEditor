import sublime
import sublime_plugin

from uuid import uuid4


###----------------------------------------------------------------------------


def yte_syntax(file):
    """
    Return the full name of a YouTube Editor syntax based on the short name.
    """
    return "Packages/YouTubeEditor/resources/syntax/%s.sublime-syntax" % file


def yte_setting(key):
    """
    Get a YouTubeEditor setting from a cached settings object.
    """
    default = yte_setting.default.get(key, None)
    return yte_setting.obj.get(key, default)


def sort_videos(video_list):
    """
    Given a list of video details returned from YouTube, sort them by video
    title. The sort is not done in place.
    """
    return sorted(video_list, key=lambda k: k["snippet.title"])


def __convert_timecode(timecode):
    """
    Takes a timecode value that's either a string or a number and returns it
    back in a number format.
    """
    if isinstance(timecode, str):
        try:
            t = timecode.split(":")
            if len(t) == 2: t.insert(0, "0")

            return (int(t[0]) * 60 * 60) + (int(t[1]) * 60) + int(t[2])
        except e as Error:
            print("YouTubeEditor:__convert_timecode() got a bad time code")
            return None

    return timecode


def make_video_link(video_id, timecode=None):
    """
    Given a video ID and an optional timecode, return back a link to that
    particular video on YouTube. Timecode can be None, a number or a string in
    ##:## format.

    None may be returned if the timecode provided isn't in a valid format.
    """
    if video_id is None:
        print("YouTubeEditor:make_video_link() no video_id provided")
        return None

    query = ""
    if timecode is not None:
        query = "?t=%d" % __convert_timecode(timecode)

    return "https://youtu.be/%s%s" % (video_id, query)


def get_video_timecode(view, event, as_string=True):
    """
    If the text under the cursor in the provided view is a timecode, capture it
    as a string and return it back. as_string controls what format the returned
    timecode will be in. None is returned if there's no timecode under the
    cursor.
    """
    if event is not None:
        pt = view.window_to_text((event["x"], event["y"]))
        if view.match_selector(pt, 'text.youtube constant.numeric.timecode'):
            timecode = view.substr(view.extract_scope(pt))
            if as_string:
                return timecode

            return __convert_timecode(timecode)

    return None


def get_window_link(view, window=None, event=None):
    """
    Make and returns a link to the video whose details are stored in the given
    window. If an event is provided and the text at the event location is a
    timecode, the generated link will include timecode information.

    If the window is not provided, it defaults to the window associated with
    the given view. If there's no window or the window has no associated video
    id, None will be returned back.
    """
    video_id = None
    timecode = get_video_timecode(view, event, False)

    window = window or view.window()
    if window is not None:
        video_id = window.settings().get("_yte_video_id")

    return make_video_link(video_id, timecode)


## ----------------------------------------------------------------------------


class BusySpinner():
    """
    A simple busy spinner in the status bar of a window. It follows the active
    view in the provided window, so you can move around and still track status.

    The spinner can be started and stopped explicitly or used as a context
    manager.
    """
    width = 5

    def __init__(self, prefix, window=None):
        self.window = window or sublime.active_window()
        self.prefix = prefix
        self.key = "__%s" % uuid4()
        self.tick_view = None
        self.running = False

    def __enter__(self):
        self.start()

    def __exit__(self, type, value, traceback):
        self.stop()

    def start(self):
        if self.running:
            raise ValueError("Cannot start spinner; already started")

        self.running = True
        sublime.set_timeout(lambda: self.update(0), 100)

    def stop(self):
        self.running = False

    def update(self, tick):
        current_view = self.window.active_view()

        if self.tick_view is not None and current_view != self.tick_view:
            self.tick_view.erase_status(self.key)
            self.tick_view = None

        if not self.running:
            current_view.erase_status(self.key)
            return

        # We need twice as many ticks as the width due to oscillation
        tick = tick % (2 * self.width)

        # Space to the left and right; once we hit half the width, go back the
        # other way.
        left = min(tick, (2 * self.width - tick))
        right = self.width - left

        # print(tick, left, right)
        text = "{} [{}={}]".format(self.prefix, " " * left, " " * right)

        current_view.set_status(self.key, text)
        if self.tick_view is None:
            self.tick_view = current_view

        sublime.set_timeout(lambda: self.update(tick + 1), 100)


## ----------------------------------------------------------------------------
