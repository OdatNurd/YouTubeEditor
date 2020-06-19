import sublime
import sublime_plugin


## ----------------------------------------------------------------------------


class YoutubeEditorNextViewCommand(sublime_plugin.WindowCommand):
    """
    This command is active only in a window that is a YouTube editor window,
    and navigates the cursor forward or backwards through the view groups in
    the window.
    """
    def run(self, prev=False):
        active = self.window.active_group()
        active = ((active + (3 - 1)) if prev else  (active + 1)) % 3

        self.window.focus_group(active)

    def is_enabled(self, prev=False):
        return self.window.settings().get("_yte_youtube_window", False)


## ----------------------------------------------------------------------------
