import sublime
import sublime_plugin

import webbrowser

from ...lib import get_video_timecode, get_window_link


## ----------------------------------------------------------------------------


class YoutubeEditorCopyVideoLinkCommand(sublime_plugin.TextCommand):
    """
    This command is active only in a window that is a YouTube editor window,
    and can copy a link to the current video to the clipboard, possibly with
    a timecode attached to it.
    """
    def run(self, edit, event=None):
        url = get_window_link(self.view, event=event)
        sublime.set_clipboard(url)
        sublime.status_message('URL Copied: %s' % url)

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
