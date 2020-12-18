import sublime
import sublime_plugin

from ...lib import log
from ..core import YoutubeRequest


###----------------------------------------------------------------------------


class YoutubeEditorFlushCacheCommand(YoutubeRequest, sublime_plugin.ApplicationCommand):
    """
    Request that the network thread flush it's cached data, forcing all future
    requests to go through to the API again.
    """
    def _authorized(self, request, result):
        self.request("flush_cache")

    def _flush_cache(self, request, result):
        log("PKG: All cached YouTube data has been flushed")


###----------------------------------------------------------------------------
