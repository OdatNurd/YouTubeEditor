import sublime
import sublime_plugin

from ...lib import log
from ..core import youtube_has_credentials
from ..core import YoutubeRequest


###----------------------------------------------------------------------------


class YoutubeEditorAuthorizeCommand(YoutubeRequest, sublime_plugin.ApplicationCommand):
    """
    Authorize the plugin to access a user's YouTube channel (i.e. "Log in").
    This will request authorization, which causes the browser to open so that
    the user can confirm that we should have access.

    This command disables itself if we have already been granted access, which
    is determined by way of having already cached credentials.
    """
    def run(self):
        self.request("authorize")

    def _authorize(self, request, result):
        log("""
            Logged into YouTube

            You are now logged into YouTube! You login credentials
            are cached and will be re-used as needed; Log out to
            clear your credentials or to access a different YouTube
            account.
            """, dialog=True)

    def is_enabled(self):
        return not youtube_has_credentials()


###----------------------------------------------------------------------------
