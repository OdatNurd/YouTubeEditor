import sublime
import sublime_plugin

from ..core import YoutubeRequest
from ...lib import yte_syntax, add_report_text, get_table_of_contents
from ...lib import make_studio_edit_link


###----------------------------------------------------------------------------


class YoutubeEditorMissingContentsCommand(YoutubeRequest,sublime_plugin.ApplicationCommand):
    """
    This command will determine which videos on the channel don't have any
    table of contents in them and display them into a report so that they can
    be edited and have contents added to them.
    """
    def _authorized(self, request, result):
        self.request("channel_list", reason="Get Channel Info")

    def _channel_list(self, request, result):
        self.channel = result[0]
        self.request("playlist_contents", reason="Get uploaded videos",
                    playlist_id=self.channel['contentDetails.relatedPlaylists.uploads'])

    def _playlist_contents(self, request, result):
        missing = [v for v in result if not get_table_of_contents(v)]
        if not missing:
            return sublime.message_dialog("All videos contain a table of contents!")

        missing = sorted(missing, key=lambda k: k["snippet.title"])
        content = ["Videos with Missing TOC in Description",
                   "--------------------------------------\n"]

        for video in missing:
            entry = "videoid={id}{title} => {url}".format(
                id=video['id'],
                title=video['snippet.title'],
                url=make_studio_edit_link(video['id']))
            content.append(entry)

        panel = add_report_text(content, caption="Missing TOC",
                                syntax=yte_syntax("YouTubeMissingTOC"))


###----------------------------------------------------------------------------

