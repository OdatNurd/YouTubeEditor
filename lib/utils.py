import sublime
import sublime_plugin

from sublime import QuickPanelItem
from uuid import uuid4


###----------------------------------------------------------------------------


# These specify the kinds to be used to classify videos in the quick panel when
# choosing; they're chosen based on the colors they have in the Adaptive
# color scheme, for lack of any better criteria.
KIND_PUBLIC =   (sublime.KIND_ID_SNIPPET,    " ", "Public Video")
KIND_UNLISTED = (sublime.KIND_ID_NAVIGATION, "U", "Unlisted Video")
KIND_PRIVATE =  (sublime.KIND_ID_FUNCTION,   "P", "Private Video")

# When browsing in the quick panel, this KIND is used to signify the special
# item that indicates that we want to go back up a level in the hierarchy.
KIND_BACK =  (sublime.KIND_ID_NAMESPACE,   "↑", "Go up one level")

# When browsing in the quick panel, this KIND is used to signify that the item
# in the list is a tag on a video.
KIND_TAG = (sublime.KIND_ID_NAMESPACE, "➤", "Video tag")

# Map YouTube video privacy values to one of our kind values.
_kind_map = {
     "private": KIND_PRIVATE,
     "public": KIND_PUBLIC,
     "unlisted": KIND_UNLISTED
}

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
        timecode = __convert_timecode(timecode)
        if timecode:
            query = "?t=%d" % timecode

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
    time code, the generated link will include time code information.

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


def select_tag(videos, callback, tag_list=None, placeholder=None):
    """
    Given a list of videos OR a list of tags, display to the user a list of all
    of the unique tags to allow them to select one. The callback is invoked
    with the selected tag and a dictionary where the keys are unique tags seen
    in the video list and the values are arrays of videos that appeared.

    Specify videos to create a tag_list (which is returned in the callback), or
    specify a previously created tag_list to reuse it.
    """
    if tag_list is None:
        tag_list = {}
        for video in videos:
            tags = video.get('snippet.tags', [])
            for tag in tags:
                if tag not in tag_list:
                    tag_list[tag] = []
                tag_list[tag].append(video)

    items = [QuickPanelItem(tag, "", "{} videos".format(len(tag_list[tag])), KIND_TAG)
                for tag in sorted(tag_list.keys())]

    sublime.active_window().show_quick_panel(items,
        lambda i: callback(None if i == -1 else items[i].trigger, tag_list),
        placeholder=placeholder)


def select_video(videos, callback, show_back=False, placeholder=None):
    """
    Given a list of video information, prompt the user with a quick panel to
    choose an item. The callback will be invoked with a single parameter; None
    if the user cancelled the selection, or the video the user selected.

    If show_back is True, an extra item is added to allow the user to go back
    to a previous panel; in this case the callback returns a video with the
    special sentinel id of "_back".
    """
    videos = sorted(videos, key=lambda k: int(k["statistics.viewCount"]), reverse=True)
    items = [QuickPanelItem(
               v['snippet.title'],
               "",
               "{0} views ✔:{1} ✘:{2}".format(
                    v['statistics.viewCount'],
                    v['statistics.likeCount'],
                    v['statistics.dislikeCount']),
               _kind_map.get(v['status.privacyStatus'], KIND_PUBLIC)
             ) for v in videos]

    if show_back:
        items.insert(0, QuickPanelItem("..", "", "Go back", KIND_BACK))

    def pick(i):
        if i == -1:
            return callback(None)

        if show_back:
            if i == 0: return callback({"id": "_back"})
            else:
                i -= 1

        callback(videos[i])

    sublime.active_window().show_quick_panel(items, pick, placeholder=placeholder)


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
