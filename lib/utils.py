import sublime
import sublime_plugin


###----------------------------------------------------------------------------


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


## ----------------------------------------------------------------------------
