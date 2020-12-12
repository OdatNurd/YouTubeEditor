import sublime
import sublime_plugin

from sublime import QuickPanelItem

from ..core import YoutubeRequest
from ...lib import dotty, make_video_link, select_video
from ...lib import select_playlist, select_tag, select_timecode


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


class YoutubeEditorGetVideoLinkCommand(YoutubeRequest, sublime_plugin.ApplicationCommand):
    """
    Generate a list of all videos for the user's YouTube channel and display
    them in a quick panel. Choosing a video from the list will copy the URL
    to the view page for that video into the clipboard.

    This command uses previously cached credentials if there are any, and
    requests the user to log in first if not.
    """
    def _authorized(self, request, result):
        self.use_tags = self.run_args.get("by_tags", False)
        self.use_playlists = self.run_args.get("by_playlists", False)
        self.request("channel_details", reason="Get Channel Info")

    def _channel_details(self, request, result):
        self.uploads_playlist = dotty(_upload_template)
        self.uploads_playlist['id'] = result['contentDetails.relatedPlaylists.uploads']

        if self.use_playlists:
            self.request("playlist_list", reason="Get user playlists")
        else:
            self.pick_playlist(self.uploads_playlist)

    def _playlist_list(self, request, result):
        playlists = sorted(result, key=lambda k: k["snippet.title"])
        playlists.insert(0, self.uploads_playlist)

        select_playlist(playlists, self.pick_playlist)

    def _playlist_contents(self, request, result):
        if self.use_tags:
            select_tag(result, self.pick_tag, show_back=self.use_playlists, placeholder="Copy video link from tag")
        else:
            # Pass the video list as the tag_list to the lambda so it can be
            # picked up and used again if the user goes back while editing the
            # timecode.
            videos = sorted(result, key=lambda k: int(k["statistics.viewCount"]), reverse=True)
            select_video(videos, lambda vid: self.select_video(vid, None, videos),
                         show_back=self.use_playlists,
                         placeholder="Copy video link")

    def pick_playlist(self, playlist):
        self.request("playlist_contents",
                      reason="Get playlist contents",
                      playlist_id=playlist['id'],
                      part="id,snippet,status,statistics",
                      full_details=True)

    def pick_tag(self, tag, tag_list):
        if tag is not None:
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
            return select_tag(None, self.pick_tag, False, tag_list)

        select_timecode(video, lambda a, b: self.pick_toc(a, b, video, tag, tag_list),
                        show_back=True)

    def pick_toc(self, timecode, text, video, tag, tag_list):
        if timecode != None:
            if timecode == "_back":
                if self.use_tags:
                    return self.pick_tag(tag, tag_list)
                else:
                    return select_video(tag_list, lambda vid: self.select_video(vid, None, None),
                                        placeholder="Copy video link")

            link = make_video_link(video['id'], timecode)
            sublime.set_clipboard(link)
            sublime.status_message('URL Copied: %s' % link)


###----------------------------------------------------------------------------
