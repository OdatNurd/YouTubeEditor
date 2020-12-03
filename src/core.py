import sublime
import sublime_plugin

import os

from ..lib import log, setup_log_panel
from ..lib import Request, NetworkManager, stored_credentials_path


# TODO:
#  - Hit the keyword in the first few lines and 2-3 times total
#  - The first few lines (how much?) are shown above the fold
#  - Tags is 500 characters long, no more than 30 characters per tag
#  - Tags with spaces may count as having a length + 2 because internally
#    they're wrapped in quotes and that counts against the length
#  - Tags should include brand related and channel tags for more relvance
#


###----------------------------------------------------------------------------


# Our global network manager object
netManager = None


###----------------------------------------------------------------------------


def loaded():
    """
    Initialize our plugin state on load.
    """
    global netManager

    for window in sublime.windows():
        setup_log_panel(window)

    log("YouTubeEditor loaded")

    netManager = NetworkManager()

    yte_setting.obj = sublime.load_settings("YouTubeEditor.sublime-settings")
    yte_setting.default = {
        "camtasia_folder": os.path.expanduser("~"),
        "auto_show_panel": 2,

        "client_id": "",
        "client_secret": "",
        "auth_uri": "",
        "token_uri": ""
    }


def unloaded():
    """
    Clean up plugin state on unload.
    """
    global netManager

    if netManager is not None:
        netManager.shutdown()
        netManager = None

def yte_syntax(file):
    """
    Return the full name of a YouTube Editor syntax based on the short name.
    """
    return "Packages/YouTubeEditor/resources/syntax/%s.sublime-syntax" % file


def yte_setting(key):
    """
    Get a YouTubeEditor setting from a cached settings object.
    """
    default = yte_setting.default.get(key, None)
    return yte_setting.obj.get(key, default)


def sort_videos(video_list):
    """
    Given a list of video details returned from YouTube, sort them by video
    title. The sort is not done in place.
    """
    return sorted(video_list, key=lambda k: k["title"])


def youtube_has_credentials():
    """
    Determine if there are stored credentials for a YouTube login; this
    indicates that the user has previously gone through the login steps to
    authorize the plugin with YouTube.
    """
    return netManager.has_credentials()


def youtube_is_authorized():
    """
    Determine if the plugin is currently authorized or not. This indicates not
    only that the user has previously authorizaed the plugin on YouTube, but
    also that a request has been made that has validated (and potentially
    refreshed) our access token. If this is not the case, requests will fail.
    """
    return netManager.is_authorized()


def youtube_request(request, handler, callback, **kwargs):
    """
    Dispatch a request to collect data from YouTube, invoking the given
    callback when the request completes. The request will store the given
    handler and all remaining arguments as arguments to the request dispatched.
    """
    netManager.request(Request(request, handler, **kwargs), callback)


###----------------------------------------------------------------------------


class YoutubeRequest():
    """
    This class abstracts away the common portions of using the NetworkManager
    to make requests and get responses back.

    A request can be made via the `request()` method, and the result will
    be automatically directed to a method in the class. The default handler
    is the name of the request preceeded by an underscore.
    """
    auth_req = None
    auth_resp = None

    def run(self, **kwargs):
        if not youtube_is_authorized():
            self.request("authorize", "_internal_auth")
        else:
            self._authorized(self.auth_req, self.auth_resp)

    def _internal_auth(self, request, result):
        self.auth_req = request
        self.auth_resp = result
        self._authorized(self.auth_req, self.auth_resp)

    def request(self, request, handler=None, **kwargs):
        youtube_request(request, handler, self.result, **kwargs)

    def result(self, request, success, result):
        attr = request.handler if success else "_error"
        if not hasattr(self, attr):
            raise RuntimeError("'%s' has no handler for request '%s'" % (
                self.name(), request.name))

        handler = getattr(self, attr)
        handler(request, result)

    def _error(self, request, result):
        log("""
            An error occured while talking to YouTube

            Request: {req}
            Result:  {err}
            """, display=True, req=request.name, err=result)

    # Assume that most commands want to only enable themselves when there are
    # credentials; commands that are responsible for obtaining credentials
    # override this method.
    def is_enabled(self, **kwargs):
        return youtube_has_credentials()


## ----------------------------------------------------------------------------
