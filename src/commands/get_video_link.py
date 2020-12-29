import sublime
import sublime_plugin


from ..core import YouTubeVideoSelect
from ...lib import make_video_link, copy_video_link


###----------------------------------------------------------------------------


class YoutubeEditorGetVideoLinkCommand(YouTubeVideoSelect, sublime_plugin.ApplicationCommand):
    """
    Prompt the user to select a timecode in a video, and then copy the link to
    that timecode (or the video in general) to the clipboard.

    The arguments by_tags and by_playlists control how the browse works; if
    provided, each one adds an extra layer of lookup to help drill down and
    find the desired video.
    """
    playlist_placeholder = "Get Link: Select a playlist"
    tag_placeholder = "Get Link: Browse by tag"
    video_placeholder = "Get Link: Select video"
    video_tag_placeholder = "Get Link: Select video in tag '{tag}'"
    timecode_placeholder = "Get Link from '{title}"

    def run(self, **kwargs):
        video_id = kwargs.get("video_id")
        timecode = kwargs.get("timecode")
        if video_id is not None:
            return self.generate_link(video_id, timecode)

        super().run(**kwargs)

    def picked_toc(self, timecode, text, video):
        self.generate_link(video['id'], timecode, video['snippet.title'])

    def generate_link(self, video_id, timecode, title=None):
        copy_video_link(make_video_link(video_id, timecode), title)

###----------------------------------------------------------------------------
