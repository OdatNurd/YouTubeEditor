import sublime
import sublime_plugin


###----------------------------------------------------------------------------


class YoutubeEditorVideoMarkupCommand(sublime_plugin.TextCommand):
    """
    This command is meant for internal YouTubeEditor use; it will find all
    instances of the meta.record.youtube scope, erase them from the buffer,
    and replace the content with an inline phantom that contains controls
    based on the information taken from the record.

    The input HTML can include the following template expansions:
        {id} : The video_id of a video
    """
    def run(self, edit, control_html):
        self.phantoms = sublime.PhantomSet(self.view, 'videoControls')
        phantoms = []

        self.view.set_read_only(False)

        adjust = 0
        for span in self.view.find_by_selector('meta.record.youtube'):
            region = sublime.Region(span.a - adjust, span.b - adjust)
            adjust += len(region)

            info = self.view.substr(region)
            video_id = info.split("=", 1)[1]

            control_html = control_html.format(id=video_id)

            self.view.erase(edit, region)

            phantoms.append(sublime.Phantom(sublime.Region(region.a),
                            control_html,
                            sublime.LAYOUT_INLINE))

        self.phantoms.update(phantoms)
        self.view.set_read_only(True)


###----------------------------------------------------------------------------

