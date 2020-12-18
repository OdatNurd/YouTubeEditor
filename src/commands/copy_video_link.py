import sublime
import sublime_plugin

import webbrowser

from ...lib import get_video_timecode, get_window_link, copy_video_link


## ----------------------------------------------------------------------------


class YoutubeEditorCopyVideoLinkCommand(sublime_plugin.TextCommand):
    """
    This command is active only in a window that is a YouTube editor window,
    and can copy a link to the current video to the clipboard, possibly with
    a timecode attached to it.
    """
    def run(self, edit, event=None):
        url = get_window_link(self.view, event=event)

        title_view = self.view.window().views_in_group(0)[0]
        title = title_view.substr(sublime.Region(0, len(title_view)))

        copy_video_link(url, title)

    def description(self, copy=True, open_in_browser=False, event=None):
        if get_video_timecode(self.view, event) != None:
            return "Copy video link at timecode"

        return "Copy video link"

    def is_enabled(self, event=None):
        s = self.view.window().settings()
        return s.get("_yte_youtube_window", False) and s.get("_yte_video_id") is not None

    def want_event(self):
        return True


## ----------------------------------------------------------------------------
