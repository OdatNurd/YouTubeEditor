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

    def picked_toc(self, timecode, text, video):
        copy_video_link(make_video_link(video['id'], timecode), video['snippet.title'])


###----------------------------------------------------------------------------
