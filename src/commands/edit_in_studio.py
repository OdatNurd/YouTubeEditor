import sublime
import sublime_plugin

import webbrowser

from ...lib import make_studio_edit_link


## ----------------------------------------------------------------------------


class YoutubeEditorEditInStudioCommand(sublime_plugin.WindowCommand):
    """
    This command is active only in a window that is a YouTube editor window,
    and can copy a link to the current video to the clipboard, possibly with
    a timecode attached to it.
    """
    def run(self, video_id=None):
        video_id = video_id or self.window.settings().get("_yte_video_id")
        webbrowser.open_new_tab(make_studio_edit_link(video_id))

    def is_enabled(self, video_id=None):
        if video_id is not None:
            return True

        s = self.window.settings()
        return s.get("_yte_youtube_window", False) and s.get("_yte_video_id") is not None


## ----------------------------------------------------------------------------
