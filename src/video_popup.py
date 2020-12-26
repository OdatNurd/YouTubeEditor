import sublime
import sublime_plugin


###----------------------------------------------------------------------------


def show_video_popup(view, point, video):
    """
    At the given point in the given view, display a hover popup for the video
    whose information is provided.

    The hover popup will contain the key information for the video, and also
    contain some links that will trigger commands that can be taken on the
    video as well.
    """
    view.show_popup(video['snippet.title'],
        flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
        location=point,
        max_width=1024,
        max_height=512)


###----------------------------------------------------------------------------

