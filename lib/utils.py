import sublime
import sublime_plugin

from sublime import QuickPanelItem
from uuid import uuid4

import re


###----------------------------------------------------------------------------


# These specify the kinds to be used to classify videos in the quick panel when
# choosing;.
KIND_PUBLIC =   (sublime.KIND_ID_SNIPPET,    " ", "Public")
KIND_UNLISTED = (sublime.KIND_ID_NAVIGATION, "U", "Unlisted")
KIND_PRIVATE =  (sublime.KIND_ID_FUNCTION,   "P", "Private")

# When browsing in the quick panel, this KIND is used to signify the special
# item that indicates that we want to go back up a level in the hierarchy.
KIND_BACK =  (sublime.KIND_ID_NAMESPACE,   "↑", "Go up one level")

# This specifies the kinds to be used when asking the user to select a timecode
# as we're choosing a video to copy the link for.
KIND_TOC = (sublime.KIND_ID_SNIPPET, "✎", "Table of Contents entry")

# When browsing in the quick panel, this KIND is used to signify that the item
# in the list is a tag on a video.
KIND_TAG = (sublime.KIND_ID_NAMESPACE, "➤", "Video tag")

# Map YouTube video privacy values to one of our kind values.
_kind_map = {
     "private": KIND_PRIVATE,
     "public": KIND_PUBLIC,
     "unlisted": KIND_UNLISTED
}

# A Regex that matches a TOC entry in a video description. This is defined as
# a line of text that starts with a timecode. Everything on the line after this
# is the chapter title in the table of contents.
_toc_regex = re.compile(r'(?m)^\s*((?:\d{1,2}:)?\d{1,2}:\d{2})\s+(.*$)')


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


def select_playlist(playlists, callback, show_back=False, placeholder=None):
    """
    Given a list of playlists, prompt the user with a quick panel to choose a
    playlist. The callback will be invoked with a single parameter; None if the
    user cancelled the selection, or the video the user selected.

    If show_back is True, an extra item is added to the list to allow the user
    to go back to a previous panel; in this case the callback returns a
    playlist with the special sentinel id of "_back".
    """
    placeholder = placeholder or "Select playlist"
    items = [QuickPanelItem(
               p['snippet.title'],
               "",
               "{0} items".format(p.get('contentDetails.itemCount', '???')),
               _kind_map.get(p['status.privacyStatus'], KIND_PRIVATE)
             ) for p in playlists]

    if show_back:
        items.insert(0, QuickPanelItem("..", "", "Go back", KIND_BACK))

    def pick(i):
        if i == -1:
            return callback(None)

        if show_back:
            if i == 0: return callback({"id": "_back"})
            else: i -= 1

        callback(playlists[i])

    sublime.active_window().show_quick_panel(items, pick, placeholder=placeholder)


def select_tag(videos, callback, show_back=False, tag_list=None, placeholder=None):
    """
    Given a list of videos OR a dictionary of tags (see below), prompt the user
    with  a quick panel to choose a tag. The callback will be invoked with two
    arguments; the name of the tag chosen, and a list of videos that contain
    that tag.

    If the user cancels the selection, both arguments will be None instead.

    If show_back is true, an extra item is added to the list to allow the user
    to go back to a previous panel; in this case the callback is invoked with
    the special sentinel tag "_back".

    The function can be given either a list of video dictionaries in videos, OR
    a dictionary of tags in tag_list. If a tag_list is provided, it is used
    directly, and will also be passed back in the callback. If tag_list is
    None, the list of videos is used to construct the tag dictionary.

    tag_list (when provided or passed to a callback) is a dictionary where the
    key is the text of a tag and the value is an array of all videos that
    contain that tag.
    """
    if tag_list is None:
        tag_list = {}
        for video in videos:
            tags = video.get('snippet.tags', [])
            for tag in tags:
                if tag not in tag_list:
                    tag_list[tag] = []
                tag_list[tag].append(video)

    placeholder = placeholder or "Browse by tag"
    items = [QuickPanelItem(tag, "", "{} videos".format(len(tag_list[tag])), KIND_TAG)
                for tag in sorted(tag_list.keys())]

    if show_back:
        items.insert(0, QuickPanelItem("..", "", "Go back", KIND_BACK))

    def pick(i):
        if i == -1:
            return callback(None, tag_list)

        if show_back:
            if i == 0: return callback("_back", tag_list)

        callback(items[i].trigger, tag_list)

    sublime.active_window().show_quick_panel(items, pick, placeholder=placeholder)


def select_video(videos, callback, show_back=False, placeholder=None):
    """
    Given a list of video records, prompt the user with a quick panel to choose
    a video. The callback will be invoked with a single parameter; None if the
    user cancelled the selection, or the video the user selected.

    If show_back is True, an extra item is added to the list to allow the user
    to go back to a previous panel; in this case the callback returns a video
    with the special sentinel id of "_back".
    """
    placeholder = placeholder or "Select video"
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
            else: i -= 1

        callback(videos[i])

    sublime.active_window().show_quick_panel(items, pick, placeholder=placeholder)


def select_timecode(video, callback, show_back=False, placeholder=None):
    """
    Given a video dictionary, display the table of contents from the
    description and prompt the user with a quick panel to choose an item. The
    callback will be invoked with two arguments; the timecode string for the
    table of contents entry, and the text of the entry itself.

    If the user cancels the selection, both arguments will be None instead.

    If show_back is True, an extra item is added to the list to allow the user
    to go back to a previous panel; in this case the timecode provided to the
    callback is the special sentinel value "_back".
    """
    toc = _toc_regex.findall(video['snippet.description'])
    if not toc:
        return callback("00:00", None)

    placeholder = placeholder or "Timecode in '%s'" % video['snippet.title']
    toc = [QuickPanelItem(i[1], "", i[0], KIND_TOC) for i in toc]

    if show_back:
        toc.insert(0, QuickPanelItem("..", "", "Go back", KIND_BACK))

    def pick(i):
        if i == -1:
            return callback(None, None)
        elif show_back and i == 0:
            return callback("_back", "")

        callback(toc[i].annotation, toc[i].trigger)

    sublime.active_window().show_quick_panel(toc, pick, placeholder=placeholder)


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
