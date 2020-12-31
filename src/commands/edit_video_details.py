import sublime
import sublime_plugin

import base64
import requests

from ..core import YouTubeVideoSelect
from ...lib import select_video, undotty_data


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

    # This overloads the base version so that if we're given an explcit video
    # ID, we will request the details for it directly instead of going through
    # everything else.
    def _authorized(self, request, result):
        self.video_id = self.run_args.get("video_id")

        self.use_tags = self.run_args.get("by_tags", False)
        self.use_playlists = self.run_args.get("by_playlists", False)

        if self.video_id:
            self.request("video_details", video_id=self.video_id,
                         refresh=True, reason="Get full video details for editing")
        else:
            self.request("channel_list", reason="Get Channel Info")


    def picked_video(self, video, tag, tag_list):
        self.request("video_details", video_id=video["id"],
                     refresh=True, reason="Get full video details for editing")

    def _video_details(self, request, result):
        video = result[0]
        sublime.active_window().run_command('youtube_editor_new_window', {
            'video_id': video["id"],
            'title': video["snippet.title"],
            'description': video["snippet.description"],
            'tags': video.get("snippet.tags", []),
            'details': undotty_data(video)
            })

        img_uri = video['snippet.thumbnails.standard.url']
        sublime.set_timeout_async(lambda: self.load_thumbnail(sublime.active_window(), img_uri))

    def load_thumbnail(self, window, img_uri):
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
