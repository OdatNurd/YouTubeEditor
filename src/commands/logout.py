import sublime
import sublime_plugin

from ...lib import log
from ..core import YoutubeRequest


###----------------------------------------------------------------------------


class YoutubeEditorLogoutCommand(YoutubeRequest, sublime_plugin.ApplicationCommand):
    """
    Remove the stored credentials that have been saved (i.e. "Log Out"). Once
    this is done, in order to make any further requests the user will have to
    re-authorize in order to re-establish the connection.
    """
    def run(self, force=False):
        if not force:
            msg = "If you proceed, you will need to re-authenticate. Continue?"
            if sublime.yes_no_cancel_dialog(msg) == sublime.DIALOG_YES:
                sublime.run_command("youtube_editor_logout", {"force": True})

            return

        self.request("deauthorize")

    def _deauthorize(self, request, result):
        log("""
            Logged out of YouTube.

            Your stored credentials have been cleared; further
            access to YouTube will require you to re-authorize
            YouTuberizer.
            """, dialog=True)


###----------------------------------------------------------------------------
