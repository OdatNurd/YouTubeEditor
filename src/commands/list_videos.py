import sublime
import sublime_plugin

from ..core import YoutubeRequest
from ...lib import sort_videos


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
        self.request("uploads_playlist")

    def _uploads_playlist(self, request, result):
        self.request("playlist_contents", playlist_id=result)

    def _playlist_contents(self, request, result):
        window = sublime.active_window()
        items = [[video['title'], video['link']] for video in sort_videos(result)]
        window.show_quick_panel(items, lambda i: self.select_video(i, items))

    def select_video(self, idx, items):
        if idx >= 0:
            video = items[idx]
            sublime.set_clipboard(video[1])
            sublime.status_message('URL Copied: %s' % video[0])


###----------------------------------------------------------------------------
