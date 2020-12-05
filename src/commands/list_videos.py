import sublime
import sublime_plugin

from ..core import YoutubeRequest
from ...lib import sort_videos, make_video_link


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
        self.request("channel_details")

    def _channel_details(self, request, result):
        self.request("playlist_contents", playlist_id=result['contentDetails.relatedPlaylists.uploads'])

    def _playlist_contents(self, request, result):
        window = sublime.active_window()
        items = [[vid['snippet.title'], make_video_link(vid['contentDetails.videoId'])]
                 for vid in sort_videos(result)]
        window.show_quick_panel(items, lambda i: self.select_video(i, items))

    def select_video(self, idx, items):
        if idx >= 0:
            video = items[idx]
            sublime.set_clipboard(video[1])
            sublime.status_message('URL Copied: %s' % video[0])


###----------------------------------------------------------------------------
