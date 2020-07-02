import sublime
import sublime_plugin

import base64
import requests

from ..core import YoutubeRequest, sort_videos


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
        self.request("uploads_playlist")

    def _uploads_playlist(self, request, result):
        self.request("playlist_contents", playlist_id=result)

    def _playlist_contents(self, request, result):
        window = sublime.active_window()
        items = [[video['title'], video['link']] for video in sort_videos(result)]
        window.show_quick_panel(items, lambda i: self.select_video(i, items))

    def _video_details(self, request, result):
        sublime.active_window().run_command('youtube_editor_new_window', {
            'video_id': result["video_id"],
            'title': result["title"],
            'description': result["description"],
            'tags': result["tags"]
            })

        sublime.set_timeout_async(lambda: self.load_thumbnail(sublime.active_window(), result["video_id"]))

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

    def select_video(self, idx, items):
        if idx >= 0:
            video = items[idx]
            video_id = video[1].split('/')[-1]
            self.request("video_details", video_id=video_id)


###----------------------------------------------------------------------------