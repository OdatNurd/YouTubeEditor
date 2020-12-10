from ...editor import reload

reload("src.commands", ["authorize", "logout", "list_videos",
                        "edit_video_details", "new_window", "navigate",
                        "get_camtasia_toc", "copy_video_link",
                        "view_video_link"])

from .authorize import YoutubeEditorAuthorizeCommand
from .logout import YoutubeEditorLogoutCommand
from .list_videos import YoutubeEditorListVideosCommand
from .edit_video_details import YoutubeEditorEditVideoDetailsCommand
from .new_window import YoutubeEditorNewWindowCommand
from .navigate import YoutubeEditorNextViewCommand
from .get_camtasia_toc import YoutubeEditorGetCamtasiaContentsCommand
from .copy_video_link import YoutubeEditorCopyVideoLinkCommand
from .view_video_link import YoutubeEditorViewVideoLinkCommand

__all__ = [
    # Authorize and Deauthorize the plugin for YouTube
    "YoutubeEditorAuthorizeCommand",
    "YoutubeEditorLogoutCommand",

    # Get the list of videos and other video details
    "YoutubeEditorListVideosCommand",
    "YoutubeEditorEditVideoDetailsCommand",

    # Open a new window with video details
    "YoutubeEditorNewWindowCommand",

    # Navigate between panes in a YouTube window
    "YoutubeEditorNextViewCommand",

    # Prompt the user for a Camtasia project file and fetch the TOC from it.
    "YoutubeEditorGetCamtasiaContentsCommand",

    # Copy a video link to the clipboard, possibly with timecode
    "YoutubeEditorCopyVideoLinkCommand",

    # View a video on YouTube, possibly with timecode
    "YoutubeEditorViewVideoLinkCommand"
]