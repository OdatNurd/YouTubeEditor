import sublime
import sublime_plugin

import os

from ..lib import log, setup_log_panel, yte_setting, dotty
from ..lib import select_video, select_playlist, select_tag, select_timecode
from ..lib import Request, NetworkManager, stored_credentials_path

# TODO:
#  - Hit the keyword in the first few lines and 2-3 times total
#  - The first few lines (how much?) are shown above the fold
#  - Tags is 500 characters long, no more than 30 characters per tag
#  - Tags with spaces may count as having a length + 2 because internally
#    they're wrapped in quotes and that counts against the length
#  - Tags should include brand related and channel tags for more relvance
#  - Chapters: first must be at 0:00; there has to be at least 3 in ascending
#    order, and the minimum length of a chapter is 10 seconds. There is no
#    official doc on what the text should look like, but observably it seems to
#    ignore leading punctuatuion, as in "00:00 - Introduction" the " - " is
#    skipped (though starting it with a literal " gets it added, so there's
#    that)


###----------------------------------------------------------------------------


# Our global network manager object
netManager = None


###----------------------------------------------------------------------------


# The uploads playlist doesn't appear in the list of playlists associated with
# a user because it's channel specific and not user specific. This is a sample
# dotty entry with just enough information to allow for populating that
# playlist into a chooser.
#
# The actual ID of the placeholder needs to be established at the point where
# the data is actually collected.
_upload_template = {
    "id": "placeholder",
    "snippet": {
        "title": "Uploaded Videos"
    },
    "status": {
        "privacyStatus": "private",
    },
    "contentDetails": {
        # We don't know how many items are in the uploads playlist until we
        # fetch the contents of it. The display code in the chooser will use
        # markup to tell the user the list size is unknown in this case.
        # "itemCount": 0
    }

}

###----------------------------------------------------------------------------


def loaded():
    """
    Initialize our plugin state on load.
    """
    global netManager

    for window in sublime.windows():
        setup_log_panel(window)

    log("PKG: YouTubeEditor loaded")

    yte_setting.obj = sublime.load_settings("YouTubeEditor.sublime-settings")
    yte_setting.default = {
        "camtasia_folder": os.path.expanduser("~"),
        "auto_show_panel": 2,

        "cache_downloaded_data": True,
        "encrypt_cache": False,

        "client_id": "",
        "client_secret": "",
        "auth_uri": "",
        "token_uri": ""
    }

    netManager = NetworkManager()


def unloaded():
    """
    Clean up plugin state on unload.
    """
    global netManager

    if netManager is not None:
        netManager.shutdown()
        netManager = None


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


def youtube_request(request, handler, reason, callback, **kwargs):
    """
    Dispatch a request to collect data from YouTube, invoking the given
    callback when the request completes. The request will store the given
    handler and all remaining arguments as arguments to the request dispatched.
    """
    netManager.request(Request(request, handler, reason, **kwargs), callback)


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

    run_args = None

    def run(self, **kwargs):
        self.run_args = kwargs

        if not youtube_is_authorized():
            self.request("authorize", "_internal_auth", "Authorizing")
        else:
            self._authorized(self.auth_req, self.auth_resp)

    def _internal_auth(self, request, result):
        self.auth_req = request
        self.auth_resp = result
        self._authorized(self.auth_req, self.auth_resp)

    def request(self, request, handler=None, reason=None, **kwargs):
        youtube_request(request, handler, reason, self.result, **kwargs)

    def result(self, request, success, result):
        attr = request.handler if success else "_error"
        if not hasattr(self, attr):
            raise RuntimeError("'%s' has no handler for request '%s'" % (
                self.name(), request.name))

        handler = getattr(self, attr)
        handler(request, result)

    def _error(self, request, result):
        log("Err: in '{0}': {2} (code={1})", request.name,
            result['error.code'], result['error.message'], display=True)

    # Assume that most commands want to only enable themselves when there are
    # credentials; commands that are responsible for obtaining credentials
    # override this method.
    def is_enabled(self, **kwargs):
        return youtube_has_credentials()


###----------------------------------------------------------------------------


class YouTubeVideoSelect(YoutubeRequest):
    """
    This class is a specialization on YoutubeRequest that specifically presumes
    that the ultimate goal is to have the user select a video for some purpose.

    The sequence of items here is:
        - Gather channel information
        - Gather list of playlists and prompt (or; assume uploads playlist)
        - Gather contents of selected playlist
        - Prompt by tags on videos in the playlist (optional based on args)
        - Prompt for a video (either in the tags or in the playlist)
        - Prompt for a timecode in the video (if any)

    """
    def _authorized(self, request, result):
        self.use_tags = self.run_args.get("by_tags", False)
        self.use_playlists = self.run_args.get("by_playlists", False)
        self.request("channel_list", reason="Get Channel Info")

    def _channel_list(self, request, result):
        self.channel = result[0]

        # Make a fake playlist from a template; populate it with the public
        # video count. The count will be adjusted later if/when the user
        # browses into the Uploads playlist.
        self.uploads_playlist = dotty.dotty(_upload_template)
        self.uploads_playlist['contentDetails.itemCount'] = self.channel['statistics.videoCount']
        self.uploads_playlist['id'] = self.channel['contentDetails.relatedPlaylists.uploads']

        if self.use_playlists:
            self.request("playlist_list", channel_id=self.channel['id'],
                         reason="Get user playlists")
        else:
            self.pick_playlist(self.uploads_playlist)

    def _playlist_list(self, request, result):
        self.playlists = sorted(result, key=lambda k: k["snippet.title"])
        self.playlists.insert(0, self.uploads_playlist)

        select_playlist(self.playlists, self.pick_playlist)

    def _playlist_contents(self, request, result):
        if self.use_tags:
            select_tag(result, self.pick_tag, show_back=self.use_playlists, placeholder="Copy video link from tag")
        else:
            # If this is the uploads playlist, update the video count to
            # include non-public videos.
            if request["playlist_id"] == self.uploads_playlist['id']:
                self.uploads_playlist['contentDetails.itemCount'] = len(result)

            # Pass the video list as the tag_list to the lambda so it can be
            # picked up and used again if the user goes back while editing the
            # timecode.
            videos = sorted(result, key=lambda k: int(k["statistics.viewCount"]), reverse=True)
            select_video(videos, lambda vid: self.select_video(vid, None, videos),
                         show_back=self.use_playlists,
                         placeholder="Copy video link")

    def pick_playlist(self, playlist):
        if playlist != None:
            self.request("playlist_contents",
                          reason="Get playlist contents",
                          playlist_id=playlist['id'])

    def pick_tag(self, tag, tag_list):
        if tag is not None:
            if tag == "_back":
                if self.use_playlists:
                    return select_playlist(self.playlists, self.pick_playlist)

            videos = sorted(tag_list[tag], key=lambda k: int(k["statistics.viewCount"]), reverse=True)

            placeholder = "Copy video link from tag '%s'" % tag
            # Video ID is in contentDetails.videoId for short results or id for
            # full details (due to it being a different type of request)
            select_video(videos, lambda vid: self.select_video(vid, tag, tag_list),
                         show_back=True, placeholder=placeholder)

    def select_video(self, video, tag, tag_list):
        if video is None:
            return

        if video['id'] == "_back":
            # When using both tags and playlists, the browse order should send
            # us back to tags first and from there to playlists.
            if self.use_tags:
                return select_tag(None, self.pick_tag, self.use_playlists, tag_list)

            return select_playlist(self.playlists, self.pick_playlist)

        self.picked_video(video, tag, tag_list)


    def pick_toc(self, timecode, text, video, tag, tag_list):
        if timecode != None:
            if timecode == "_back":
                if self.use_tags:
                    return self.pick_tag(tag, tag_list)
                else:
                    return select_video(tag_list, lambda vid: self.select_video(vid, None, None),
                                        show_back=self.use_playlists,
                                        placeholder="Copy video link")

            self.picked_toc(timecode, text, video)

    def picked_video(self, video, tag, tag_list):
        """
        Override this if you want to know what video the user selected; the
        default will continue on to prompt the user for a timecode contained
        in the video instead.

        video represents the video chosen by the user, and tag is the tag they
        chose (if prompted; otherwise it is None). The tag_list argument should
        be ignored by outside code, as its value and use changes depending on
        how the user is browsing around in the content.
        """
        select_timecode(video, lambda a, b: self.pick_toc(a, b, video, tag, tag_list),
                        show_back=True)

    def picked_toc(self, timecode, text, video):
        """
        Override this if you want to know what timecode the user selected from
        the table of contents of their selected video. You get told the
        timecode string, the text of the TOC entry associated with it, and the
        information on the video the user selected.
        """
        pass


###----------------------------------------------------------------------------
