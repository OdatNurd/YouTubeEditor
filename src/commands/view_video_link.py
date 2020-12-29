import sublime
import sublime_plugin

import webbrowser

from ...lib import get_video_timecode, make_video_link, get_window_link


## ----------------------------------------------------------------------------


class YoutubeEditorViewVideoLinkCommand(sublime_plugin.TextCommand):
    """
    This command is active only in a window that is a YouTube editor window or
    when given an explicit video ID, and will open the video in a browser,
    possibly at a timecode.
    """
    def run(self, edit, video_id=None, timecode=None, event=None):
        url = (make_video_link(video_id, timecode) if video_id
               else get_window_link(self.view, event=event))
        webbrowser.open_new_tab(url)

    def description(self, copy=True, open_in_browser=False, event=None):
        if get_video_timecode(self.view, event) != None:
            return "View on YouTube at timecode"

        return "View on YouTube"

    def is_enabled(self, video_id=None, timecode=None, event=None):
        s = self.view.window().settings()
        return (video_id is not None or
               (s.get("_yte_youtube_window", False) and s.get("_yte_video_id")))

    def want_event(self):
        return True


## ----------------------------------------------------------------------------
