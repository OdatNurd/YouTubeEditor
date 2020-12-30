import sublime
import sublime_plugin

from ..core import YoutubeRequest
from ...lib import log


## ----------------------------------------------------------------------------


# These represent the keys that we're allowed to put into the updated video
# details when we ask YouTube to modify the details on a video.
_top_keys = {
    "id", "snippet", "status"
}
_snippet_keys = {
    "title", "categoryId", "categoryId", "defaultLanguage", "description",
    "tags", "title"
}
_status_keys = {
    "embeddable", "license", "privacyStatus", "publicStatsViewable",
    "selfDeclaredMadeForKids"
}


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

# id
# snippet.title
# snippet.categoryId

# snippet.categoryId
# snippet.defaultLanguage
# snippet.description
# snippet.tags[]
# snippet.title

# status.embeddable
# status.license
# status.privacyStatus
# status.publicStatsViewable
# status.selfDeclaredMadeForKids



    def get_edited_details(self):
        details = self.window.settings().get("_yte_video_details")

        tags = self.get_new_data(2).split(",")

        details['snippet']['title'] = self.get_new_data(0)
        details['snippet']['description'] = self.get_new_data(1)
        details['snippet']['tags'] = [t.strip() for t in tags if t != ''];

        keys = _top_keys & set(details.keys())
        print(keys)
        new_details = {key: details[key] for key in keys}

        snippet = new_details["snippet"]
        keys = _snippet_keys & set(snippet.keys())
        print(keys)
        new_details["snippet"] = {key: snippet[key] for key in keys}

        status = new_details["status"]
        keys = _status_keys & set(status.keys())
        print(keys)
        new_details["status"] = {key: status[key] for key in keys}

        return new_details

    def get_new_data(self, group):
        view = self.window.views_in_group(group)[0]
        return view.substr(sublime.Region(0, len(view))).strip()

    def is_enabled(self):
        s = self.window.settings()
        return (s.get("_yte_youtube_window", False) and
                s.get("_yte_video_id") is not None and
                s.get("_yte_video_details") is not None)


## ----------------------------------------------------------------------------
