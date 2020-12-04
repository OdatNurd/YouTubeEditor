import sublime
import sublime_plugin

import webbrowser

from ...lib import get_video_timecode, get_window_link


## ----------------------------------------------------------------------------


class YoutubeEditorGetVideoLinkCommand(sublime_plugin.TextCommand):
    """
    This command is active only in a window that is a YouTube editor window,
    and can copy a link to the current video to the clipboard, possibly with
    a timecode attached to it.
    """
    def run(self, edit, copy=True, open_in_browser=False, event=None):
        url = get_window_link(self.view, event=event)
        if copy:
            sublime.set_clipboard(url)
            sublime.status_message('URL Copied: %s' % url)

        if open_in_browser:
            webbrowser.open_new_tab(url)

    def description(self, copy=True, open_in_browser=False, event=None):
        if get_video_timecode(self.view, event) != None:
            if copy:
                return "Copy video link at timecode"

            return "View on YouTube at timecode"

        if copy:
            return "Copy video link"

        return "View on YouTube"

    def is_enabled(self, event=None):
        s = self.view.window().settings()
        return s.get("_yte_youtube_window", False) and s.get("_yte_video_id") is not None

    def want_event(self):
        return True


## ----------------------------------------------------------------------------
