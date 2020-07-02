import sublime
import sublime_plugin


from ..lib import log


###----------------------------------------------------------------------------


def check_length(view, max_length, key, scope):
    length = len(view)
    if length > max_length:
        view.add_regions(key, [sublime.Region(max_length, length)], scope)
    else:
        view.erase_regions(key)

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


