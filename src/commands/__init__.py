from ...editor import reload

reload("src.commands", ["authorize", "logout", "list_videos", "new_window",
                        "video_details", "navigate", "get_camtasia_toc"])

from .authorize import YoutubeEditorAuthorizeCommand
from .logout import YoutubeEditorLogoutCommand
from .list_videos import YoutubeEditorListVideosCommand
from .video_details import YoutubeEditorVideoDetailsCommand
from .new_window import YoutubeEditorNewWindowCommand
from .navigate import YoutubeEditorNextViewCommand
from .get_camtasia_toc import YoutubeEditorGetCamtasiaContentsCommand
from .get_video_link import YoutubeEditorGetVideoLinkCommand

__all__ = [
    # Authorize and Deauthorize the plugin for YouTube
    "YoutubeEditorAuthorizeCommand",
    "YoutubeEditorLogoutCommand",

    # Get the list of videos and other video details
    "YoutubeEditorListVideosCommand",
    "YoutubeEditorVideoDetailsCommand",

    # Open a new window with video details
    "YoutubeEditorNewWindowCommand",

    # Navigate between panes in a YouTube window
    "YoutubeEditorNextViewCommand",

    # Prompt the user for a Camtasia project file and fetch the TOC from it.
    "YoutubeEditorGetCamtasiaContentsCommand",

    # Copy a video link to the clipboard, possibly with timecode
    "YoutubeEditorGetVideoLinkCommand"
]