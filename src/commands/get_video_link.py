import sublime
import sublime_plugin

from sublime import QuickPanelItem

from ..core import YoutubeRequest
from ...lib import make_video_link, select_video

import re


###----------------------------------------------------------------------------


# A Regex that matches a TOC entry in a video description. This is defined as
# a line of text that starts with a timecode. Everything on the line after this
# is the chapter title in the table of contents.
_toc_regex = re.compile(r'(?m)^\s*((?:\d{1,2}:)?\d{1,2}:\d{2})\s+(.*$)')

# This specifies the kinds to be used when asking the user to select a timecode
# as we're choosing a video to copy the link for. The base kind is chosen based
# on its color in Adaptive for lack of any better criteria.
KIND_TOC = (sublime.KIND_ID_SNIPPET, "✎", "Table of Contents entry")


###----------------------------------------------------------------------------


class YoutubeEditorGetVideoLinkCommand(YoutubeRequest, sublime_plugin.ApplicationCommand):
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
                      part="id,snippet,status,statistics",
                      full_details=True)

    def _playlist_contents(self, request, result):
        # Video ID is in contentDetails.videoId for short results or id for
        # full details (due to it being a different type of request)
        select_video(result, lambda vid: self.select_video(vid),
                     "Copy Video Link")

    def select_video(self, video):
        if video is None:
            return

        toc = _toc_regex.findall(video['snippet.description'])
        if not toc:
            return self.link_at_timecode(video)

        placeholder = "Timecode in '%s'" % video['snippet.title']
        toc = [QuickPanelItem(i[1], "", i[0], KIND_TOC) for i in toc]
        sublime.active_window().show_quick_panel(toc,
                                                lambda i: self.pick_toc(i, toc, video),
                                                placeholder=placeholder)

    def pick_toc(self, idx, toc, video):
        if idx != -1:
            self.link_at_timecode(video, toc[idx].annotation)

    def link_at_timecode(self, video, timecode=None):
        link = make_video_link(video['id'], timecode)
        sublime.set_clipboard(link)
        sublime.status_message('URL Copied: %s' % link)


###----------------------------------------------------------------------------
