import sublime
import sublime_plugin

from ..core import YoutubeRequest
from ...lib import log, undotty_data


## ----------------------------------------------------------------------------


def _groups_have_changes(window, groups):
    """
    Check the first view in the given group or groups of the provided window to
    see if they have any changes made to them.

    This requires that the tracking variables that we use to know about changes
    in our scratch YouTubeEditor buffers have been set up.
    """
    if not isinstance(groups, list):
        groups = [groups]

    for group in groups:
        view = window.views_in_group(group)[0]
        settings = view.settings()

        # Never allow an empty view to count as changes, so we don't clobber
        # data with nothing.
        if view.size() == 0:
            return False

        # If the change count is the same, we're good.
        if view.change_count() == settings.get("_yte_change_count", -1):
            continue

        # If the content is the same, we're good (but update the stored change
        # count so we don't need to do this next time).
        elif view.substr(sublime.Region(0, len(view))) == settings.get("_yte_content"):
            settings.set("_yte_change_count", view.change_count())
            continue

        return True

    return False


###----------------------------------------------------------------------------


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
        self.update_stored_data(result)

        log("PKG: Video details saved!")
        sublime.status_message("Video details successfully updated!")

    def get_edited_details(self):
        details = self.window.settings().get("_yte_video_details")

        details['snippet']['title'] = self.get_new_data(0)
        details['snippet']['description'] = self.get_new_data(1)

        tags = self.get_new_data(2).split(",")
        details['snippet']['tags'] = [t.strip() for t in tags if t != ''];

        return details

    def update_stored_data(self, result):
        self.window.settings().set("_yte_video_details", undotty_data(result))

        for group in range(3):
            view = self.window.views_in_group(group)[0]
            view.settings().set("_yte_change_count", view.change_count())
            view.settings().set("_yte_content", view.substr(sublime.Region(0, len(view))))

    def get_new_data(self, group):
        view = self.window.views_in_group(group)[0]
        return view.substr(sublime.Region(0, len(view))).strip()

    def is_enabled(self):
        s = self.window.settings()
        return (s.get("_yte_youtube_window", False) and
                s.get("_yte_video_id") is not None and
                s.get("_yte_video_details") is not None and
                _groups_have_changes(self.window, [0, 1, 2]))


## ----------------------------------------------------------------------------
