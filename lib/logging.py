import sublime

import textwrap


###----------------------------------------------------------------------------


def log(msg, *args, dialog=False, error=False, panel=False, **kwargs):
    """
    Generate a log message to the console, and then also optionally to a dialog
    or decorated output panel.

    The message will be formatted and dedented before being displayed and will
    have a prefix that indicates where it's coming from.
    """
    msg = textwrap.dedent(msg.format(*args, **kwargs)).strip()

    # sublime.error_message() always displays its content in the console
    if error:
        print("YouTubeEditor:")
        return sublime.error_message(msg)

    for line in msg.splitlines():
        print("YouTubeEditor: {msg}".format(msg=line))

    if dialog:
        sublime.message_dialog(msg)

    if panel:
        window = sublime.active_window()
        if "output.youtubeeditor" not in window.panels():
            view = window.create_output_panel("youtubeeditor")
            view.set_read_only(True)
            view.settings().set("gutter", False)
            view.settings().set("rulers", [])
            view.settings().set("word_wrap", False)

        view = window.find_output_panel("youtubeeditor")
        view.run_command("append", {
            "characters": msg + "\n",
            "force": True,
            "scroll_to_end": True})

        window.run_command("show_panel", {"panel": "output.youtubeeditor"})


###----------------------------------------------------------------------------
