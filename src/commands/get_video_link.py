import sublime
import sublime_plugin

import webbrowser


## ----------------------------------------------------------------------------


class YoutubeEditorGetVideoLinkCommand(sublime_plugin.TextCommand):
    """
    This command is active only in a window that is a YouTube editor window,
    and can copy a link to the current video to the clipboard, possibly with
    a timecode attached to it.
    """
    def run(self, edit, copy=True, open_in_browser=False, event=None):
        video_id = self.view.window().settings().get("_yte_video_id")
        url = "https://youtu.be/%s%s" % (video_id, self.get_time_query(event))
        if copy:
            sublime.set_clipboard(url)
            sublime.status_message('URL Copied: %s' % url)

        if open_in_browser:
            webbrowser.open_new_tab(url)

    def description(self, copy=True, open_in_browser=False, event=None):
        if self.get_time_query(event) != "":
            if copy:
                return "Copy video link at timecode"

            return "View on YouTube at timecode"

        if copy:
            return "Copy video link"

        return "View on YouTube"

    def get_time_query(self, event):
        if event is not None:
            point = self.view.window_to_text((event["x"], event["y"]))
            if self.view.match_selector(point, 'constant.numeric.timecode'):
                timecode = self.view.substr(self.view.extract_scope(point))
                return "?t=%d" % (int(timecode[:2]) * 60 + int(timecode[3:]))

        return ""

    def is_enabled(self, event=None):
        s = self.view.window().settings()
        return s.get("_yte_youtube_window", False) and s.get("_yte_video_id") is not None

    def want_event(self):
        return True


## ----------------------------------------------------------------------------
