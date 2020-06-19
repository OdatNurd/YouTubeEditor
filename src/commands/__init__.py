from ...editor import reload

reload("src.commands", ["authorize", "logout", "list_videos", "new_window",
                        "video_details", "navigate"])

from .authorize import YoutubeEditorAuthorizeCommand
from .logout import YoutubeEditorLogoutCommand
from .list_videos import YoutubeEditorListVideosCommand
from .video_details import YoutubeEditorVideoDetailsCommand
from .new_window import YoutubeEditorNewWindowCommand
from .navigate import YoutubeEditorNextViewCommand

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
    "YoutubeEditorNextViewCommand"
]