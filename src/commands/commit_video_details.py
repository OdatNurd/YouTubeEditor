import sublime
import sublime_plugin

from ..core import YoutubeRequest
from ...lib import log


## ----------------------------------------------------------------------------


class YoutubeEditorCommitDetailsCommand(YoutubeRequest,sublime_plugin.WindowCommand):
    """
    This command is active only in a window that is a YouTube editor window
    that also has an associated video id and video details. It will attempt to
    shuttle changes made in this view up to YouTube.
    """
    part = "snippet,contentDetails,status,statistics"

    def _authorized(self, request, result):
        self.request("set_video_details",
                     part=self.part,
                     video_details=self.get_edited_details())

    def _set_video_details(self, request, result):
        log("PKG: Video details saved!")


    def get_edited_details(self):
        details = self.window.settings().get("_yte_video_details")

        details['snippet']['title'] = self.get_new_data(0)
        details['snippet']['description'] = self.get_new_data(1)

        tags = self.get_new_data(2).split(",")
        details['snippet']['tags'] = [t.strip() for t in tags if t != ''];

        return details

    def get_new_data(self, group):
        view = self.window.views_in_group(group)[0]
        return view.substr(sublime.Region(0, len(view))).strip()

    def is_enabled(self):
        s = self.window.settings()
        return (s.get("_yte_youtube_window", False) and
                s.get("_yte_video_id") is not None and
                s.get("_yte_video_details") is not None)


## ----------------------------------------------------------------------------
