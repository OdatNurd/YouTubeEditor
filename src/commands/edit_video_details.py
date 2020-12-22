import sublime
import sublime_plugin

import base64
import requests

from ..core import YouTubeVideoSelect
from ...lib import select_video


###----------------------------------------------------------------------------


class YoutubeEditorEditVideoDetailsCommand(YouTubeVideoSelect, sublime_plugin.ApplicationCommand):
    """
    Prompt the user to select a video, and then display the details of that
    video in a window for further editing.

    The arguments by_tags and by_playlists control how the browse works; if
    provided, each one adds an extra layer of lookup to help drill down and
    find the desired video.
    """
    playlist_placeholder = "Edit Details: Select a playlist"
    tag_placeholder = "Edit Details: Browse by tag"
    video_placeholder = "Edit Details: Select video"
    video_tag_placeholder = "Edit Details: Select video in tag '{tag}'"

    def picked_video(self, video, tag, tag_list):
        self.request("video_details", video_id=video["id"],
                     reason="Get full video details for editing")

    def _video_details(self, request, result):
        video = result[0]
        sublime.active_window().run_command('youtube_editor_new_window', {
            'video_id': video["id"],
            'title': video["snippet.title"],
            'description': video["snippet.description"],
            'tags': video.get("snippet.tags", []),
            'details': video.to_dict()
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
