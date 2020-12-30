from ...editor import reload

reload("src.commands", ["authorize", "logout", "get_video_link",
                        "edit_video_details", "new_window", "navigate",
                        "get_camtasia_toc", "copy_video_link", "edit_in_studio",
                        "view_video_link", "clear_log", "flush_cache",
                        "missing_toc_util", "commit_video_details"])

from .authorize import YoutubeEditorAuthorizeCommand
from .logout import YoutubeEditorLogoutCommand
from .get_video_link import YoutubeEditorGetVideoLinkCommand
from .edit_video_details import YoutubeEditorEditVideoDetailsCommand
from .new_window import YoutubeEditorNewWindowCommand
from .navigate import YoutubeEditorNextViewCommand
from .get_camtasia_toc import YoutubeEditorGetCamtasiaContentsCommand
from .copy_video_link import YoutubeEditorCopyVideoLinkCommand
from .view_video_link import YoutubeEditorViewVideoLinkCommand
from .edit_in_studio import YoutubeEditorEditInStudioCommand
from .commit_video_details import YoutubeEditorCommitDetailsCommand
from .clear_log import YoutubeEditorClearLogCommand
from .flush_cache import YoutubeEditorFlushCacheCommand
from .missing_toc_util import YoutubeEditorMissingContentsCommand

__all__ = [
    # Authorize and Deauthorize the plugin for YouTube
    "YoutubeEditorAuthorizeCommand",
    "YoutubeEditorLogoutCommand",

    # Get the list of videos and other video details
    "YoutubeEditorGetVideoLinkCommand",
    "YoutubeEditorEditVideoDetailsCommand",
    "YoutubeEditorEditInStudioCommand",
    "YoutubeEditorCommitDetailsCommand",

    # Open a new window with video details
    "YoutubeEditorNewWindowCommand",

    # Navigate between panes in a YouTube window
    "YoutubeEditorNextViewCommand",

    # Prompt the user for a Camtasia project file and fetch the TOC from it.
    "YoutubeEditorGetCamtasiaContentsCommand",

    # Copy a video link to the clipboard, possibly with timecode
    "YoutubeEditorCopyVideoLinkCommand",

    # View a video on YouTube, possibly with timecode
    "YoutubeEditorViewVideoLinkCommand",

    # Clear the contents of the log panel
    "YoutubeEditorClearLogCommand",

    # Flush the network request cache
    "YoutubeEditorFlushCacheCommand",

    # Utility commands
    "YoutubeEditorMissingContentsCommand",
]