import sublime
import sublime_plugin

import datetime
import os

from ..core import YoutubeRequest
from ...lib import sort_videos, yte_setting


###----------------------------------------------------------------------------


def _get_toc(content):
    try:
        data = sublime.decode_value(content)
        toc = data["timeline"]["parameters"]["toc"]["keyframes"]

        result = []
        for entry in toc:
            time = int(entry["time"]) / 30
            text = entry["value"]

            timecode = datetime.datetime(100, 1, 1, 0, 0, 0) + datetime.timedelta(0, time)
            result.append("%s %s" % (timecode.strftime("%M:%S"), text))

        return "\n".join(result)

    except Exception as e:
        print(e)
        return None


###----------------------------------------------------------------------------


class YoutubeEditorGetCamtasiaContentsCommand(sublime_plugin.ApplicationCommand):
    """
    Prompt the user for a Camtasia project filename, then load the Table of
    Contents from the project and insert it into the currently active buffer
    or copy it to the clipboard, depending on the value of the insert argument.

    If a filename is provided, it's used directly; otherwise, the user will be
    prompted to select a filename.
    """
    last_folder = None

    def run(self, filename=None, insert=False):
        if filename is None:
            default_folder = yte_setting("camtasia_folder")

            self.last_folder = self.last_folder or default_folder

            return sublime.open_dialog(lambda f: self.pick_file(f, insert),
                [("Camtasia Projects", "*.tscproj")],
                self.last_folder, False, False)

        self.last_folder = os.path.dirname(filename)

        try:
            window = sublime.active_window()

            with open(filename, "rt") as handle:
                result = _get_toc(handle.read())

            if result is not None:
                if insert:
                    window.run_command("insert", {"characters": result})
                else:
                    sublime.set_clipboard(result)
                    window.status_message("Copied video TOC to Clipboard")
            else:
                window.status_message("Error extracting TOC data")

        except Exception as e:
            print(e)

    def is_enabled(self, filename=None, insert=False):
        if insert:
            return sublime.active_window().active_view().match_selector(0, "text.youtube.body")

        # If we're not doing a direct insert, the command will copy to the
        # clipboard, so always allow that.
        return True

    def pick_file(self, filename, insert):
        if filename is not None:
            self.run(filename, insert)


###----------------------------------------------------------------------------
