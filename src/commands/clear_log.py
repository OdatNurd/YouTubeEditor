import sublime
import sublime_plugin

from ...lib import setup_log_panel


###----------------------------------------------------------------------------


class YoutubeEditorClearLogCommand(sublime_plugin.ApplicationCommand):
    """
    Clear the contents out of the YouTube log panel in all available windows.
    """
    def run(self):
        for window in sublime.windows():
            setup_log_panel(window)


###----------------------------------------------------------------------------
