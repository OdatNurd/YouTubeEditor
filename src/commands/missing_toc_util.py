import sublime
import sublime_plugin

from ..core import YoutubeRequest
from ...lib import yte_syntax, add_report_text, get_table_of_contents
from ...lib import video_sort, make_studio_edit_link


###----------------------------------------------------------------------------


_controls_html = """
<body id="my-plugin-feature">
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            background-color: transparent;
        }}
        a {{
            text-decoration: none;
            font-size: 0.8rem;
        }}
    </style>
    [<a href="subl:youtube_editor_edit_in_studio {{&quot;video_id&quot;:&quot;{id}&quot;}}">Edit</a>]
</body>
"""

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
        missing = [v for v in video_sort(result, 'snippet.title') if not get_table_of_contents(v)]
        if not missing:
            return sublime.message_dialog("All videos contain a table of contents!")

        content = ["Videos with Missing TOC in Description",
                   "--------------------------------------\n"]

        for video in missing:
            entry = "videoid={id}{title}".format(id=video['id'],
                                                  title=video['snippet.title'])
            content.append(entry)

        panel = add_report_text(content, caption="Missing TOC",
                                syntax=yte_syntax("YouTubeMissingTOC"))

        panel.run_command("youtube_editor_video_markup", {
            "control_html": _controls_html
        })


###----------------------------------------------------------------------------

