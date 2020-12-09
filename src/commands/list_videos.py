import sublime
import sublime_plugin

from ..core import YoutubeRequest
from ...lib import make_video_link, select_video


###----------------------------------------------------------------------------


class YoutubeEditorListVideosCommand(YoutubeRequest, sublime_plugin.ApplicationCommand):
    """
    Generate a list of all videos for the user's YouTube channel and display
    them in a quick panel. Choosing a video from the list will copy the URL
    to the view page for that video into the clipboard.

    This command uses previously cached credentials if there are any, and
    requests the user to log in first if not.
    """
    def _authorized(self, request, result):
        self.request("channel_details", reason="Get Channel Info")

    def _channel_details(self, request, result):
        self.request("playlist_contents",
                      reason="Get Uploaded Videos",
                      playlist_id=result['contentDetails.relatedPlaylists.uploads'],
                      full_details=True)

    def _playlist_contents(self, request, result):
        # Video ID is in contentDetails.videoId for short results or id for
        # full details (due to it being a different type of request)
        select_video(result, lambda vid: self.select_video(vid))

    def select_video(self, video):
        if video:
            link = make_video_link(video['id'])
            sublime.set_clipboard(link)
            sublime.status_message('URL Copied: %s' % link)


###----------------------------------------------------------------------------
