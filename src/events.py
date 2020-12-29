import sublime
import sublime_plugin

from ..lib import log, setup_log_panel, dotty
from .video_popup import show_video_popup

from bisect import bisect_left


###----------------------------------------------------------------------------


def check_length(view, max_length, key, scope):
    length = len(view)
    if length > max_length:
        view.add_regions(key, [sublime.Region(max_length, length)], scope)
    else:
        view.erase_regions(key)

###----------------------------------------------------------------------------


class GlobalYouTubeEventListener(sublime_plugin.EventListener):
    """
    Handle any global events that don't need to be handled only in specific
    views.
    """
    def on_new_window(self, window):
        for existing in sublime.windows():
            if existing.id() != window.id():
                return setup_log_panel(window, existing)


###----------------------------------------------------------------------------


class YoutubeTitleEventListener(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        return settings.get("_yte_video_title", False)

    def on_modified(self):
        check_length(self.view, 100, '_yt_title_len', 'region.redish')


###----------------------------------------------------------------------------


class YoutubeBodyEventListener(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        return settings.get("_yte_video_body", False)

    def on_modified(self):
        check_length(self.view, 5000, '_yt_body_len', 'region.redish')

        timecodes = self.view.find_by_selector('constant.numeric.timecode')
        self.view.add_regions('timecodes', timecodes, 'constant.numeric',
            flags=sublime.DRAW_STIPPLED_UNDERLINE | sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)


###----------------------------------------------------------------------------


class YoutubeTagsEventListener(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        return settings.get("_yte_video_tags", False)

    def on_modified(self):
        check_length(self.view, 500, '_yt_tags_len', 'region.redish')

        errs = []
        for r in self.view.find_by_selector('variable.function.tags'):
            if len(r) > 28:
                errs.append(r)

        if errs:
            self.view.add_regions('_yt_tag_body', errs, 'region.redish',
                flags=sublime.DRAW_NO_FILL)
        else:
            self.view.erase_regions('_yt_tag_body')


###----------------------------------------------------------------------------


class YouTubeVideoReportEventListener(sublime_plugin.EventListener):
    def on_hover(self, view, point, hover_zone):
        s = view.settings()
        if not (s.get("_yte_video_ids") and s.get("_yte_video_info")):
            return

        if (hover_zone != sublime.HOVER_TEXT or
            not view.match_selector(point, 'meta.title.youtube')):
            return

        video_info = self._get_video_info(view, point)
        if video_info:
            show_video_popup(view, point, video_info)

    def _get_video_info(self, view, point):
        ids = view.settings().get("_yte_video_ids")
        info = view.settings().get("_yte_video_info")

        try:
            title_region = view.extract_scope(point)
            titles = view.find_by_selector('meta.title.youtube')
            idx = bisect_left(titles, title_region)

            if idx != len(titles) and titles[idx] == title_region:
                video_id = ids[idx]
                return dotty.Dotty(info[video_id])
        except:
            pass

        return None


###----------------------------------------------------------------------------
