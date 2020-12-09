import sublime
import sublime_plugin

import base64
import requests

from ..core import YoutubeRequest
from ...lib import select_video


###----------------------------------------------------------------------------


class YoutubeEditorVideoDetailsCommand(YoutubeRequest, sublime_plugin.ApplicationCommand):
    """
    Generate a list of all videos for the user's YouTube channel and display
    them in a quick panel. Choosing a video from the list will open a new
    editor window displaying the details for that video.

    This command uses previously cached credentials if there are any, and
    requests the user to log in first if not.
    """
    def _authorized(self, request, result):
        self.request("channel_details", reason="Get Channel Info")

    def _channel_details(self, request, result):
        self.request("playlist_contents",
                      reason="Get Uploaded Videos",
                      playlist_id=result['contentDetails.relatedPlaylists.uploads'],
                      part="id,snippet,status,statistics",
                      full_details=True)

    def _playlist_contents(self, request, result):
        # Video ID is in contentDetails.videoId for short results or id for
        # full details (due to it being a different type of request)
        select_video(result, lambda vid: self.select_video(vid),
                     "View Video Details")

    # TODO: Currently, the playlist contents being full_details already
    # contains the full video details so this request is redundant. However if
    # we update full_details to not be full details, this might still be
    # needed.
    def _video_details(self, request, result):
        sublime.active_window().run_command('youtube_editor_new_window', {
            'video_id': result["id"],
            'title': result["snippet.title"],
            'description': result["snippet.description"],
            'tags': result.get("snippet.tags", [])
            })

        sublime.set_timeout_async(lambda: self.load_thumbnail(sublime.active_window(), result["id"]))

    def load_thumbnail(self, window, video_id):
        img_uri = 'https://i.ytimg.com/vi/%s/sddefault.jpg' % video_id
        try:
            request = requests.get(img_uri, stream=True)
            data_uri = ("data:" + request.headers['Content-Type'] + ";" +
                "base64," + base64.b64encode(request.content).decode("utf-8"))

            prev_group = window.active_group()
            window.new_html_sheet('Video Thumbnail', '<img src="%s" />' % data_uri, group=3)
            window.focus_group(prev_group)
        except:
            pass

    def select_video(self, video):
        if video:
            self.request("video_details", video_id=video['id'],
                         reason="Get Video Details")


###----------------------------------------------------------------------------
