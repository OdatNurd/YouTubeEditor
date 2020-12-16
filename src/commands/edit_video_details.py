import sublime
import sublime_plugin

import base64
import requests

from ..core import YoutubeRequest
from ...lib import select_video


###----------------------------------------------------------------------------


class YoutubeEditorEditVideoDetailsCommand(YoutubeRequest, sublime_plugin.ApplicationCommand):
    """
    Generate a list of all videos for the user's YouTube channel and display
    them in a quick panel. Choosing a video from the list will open a new
    editor window displaying the details for that video for viewing and future
    editing.

    This command uses previously cached credentials if there are any, and
    requests the user to log in first if not.
    """
    def _authorized(self, request, result):
        self.request("channel_list", reason="Get Channel Info")

    def _channel_list(self, request, result):
        self.channel = result[0]
        self.request("playlist_contents",
                      reason="Get Uploaded Videos",
                      playlist_id=self.channel['contentDetails.relatedPlaylists.uploads'],
                      part="id,snippet,status,statistics",
                      full_details=True)

    def _playlist_contents(self, request, result):
        select_video(result, lambda video: self.select_video(video),
                     "Edit Video Details")

    def select_video(self, video):
        if video:
            sublime.active_window().run_command('youtube_editor_new_window', {
                'video_id': video["id"],
                'title': video["snippet.title"],
                'description': video["snippet.description"],
                'tags': video.get("snippet.tags", [])
                })

            sublime.set_timeout_async(lambda: self.load_thumbnail(sublime.active_window(), video["id"]))

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


###----------------------------------------------------------------------------
