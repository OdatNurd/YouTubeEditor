import sublime
import sublime_plugin

from sublime import QuickPanelItem

from ..core import YoutubeRequest
from ...lib import make_video_link, select_video, select_tag, select_timecode


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
        self.request("channel_details", reason="Get Channel Info")

    def _channel_details(self, request, result):
        self.request("playlist_contents",
                      reason="Get Uploaded Videos",
                      playlist_id=result['contentDetails.relatedPlaylists.uploads'],
                      part="id,snippet,status,statistics",
                      full_details=True)

    def _playlist_contents(self, request, result):
        if self.use_tags:
            select_tag(result, self.pick_tag, False, placeholder="Copy video link from tag")
        else:
            # Pass the video list as the tag_list to the lambda so it can be
            # picked up and used again if the user goes back while editing the
            # timecode.
            select_video(result, lambda vid: self.select_video(vid, None, result),
                         placeholder="Copy video link")

    def pick_tag(self, tag, tag_list):
        if tag is not None:
            videos = tag_list[tag]

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
