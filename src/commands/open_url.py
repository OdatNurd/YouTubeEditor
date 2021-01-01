import sublime
import sublime_plugin

import webbrowser

from ..core import YoutubeRequest


###----------------------------------------------------------------------------


class YoutubeEditorOpenUrlCommand(YoutubeRequest, sublime_plugin.ApplicationCommand):
    """
    Expand variables related to the current user's YouTube channel and videos,
    and open them in the default browser.
    """
    def _authorized(self, request, result):
        self.request("channel_list")

    def _channel_list(self, request, result):
        variables = {
            "channel_id": result[0]['id']
        }
        url = sublime.expand_variables(self.run_args.get("url", ""), variables)
        if url:
            webbrowser.open_new_tab(url)


###----------------------------------------------------------------------------
