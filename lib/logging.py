import sublime

import textwrap

from .utils import yte_setting


###----------------------------------------------------------------------------


def log(msg, *args, dialog=False, error=False, panel=True, display=False, **kwargs):
    """
    Generate a log message to the console, and then also optionally to a dialog
    or decorated output panel.

    The message will be formatted and dedented before being displayed and will
    have a prefix that indicates where it's coming from.

    Setting display to true will cause the output panel to open, but only when
    panel is also set; this allows the code to display informational messages
    to the panel and only display it when they might require user attention.
    """
    msg = textwrap.dedent(msg.format(*args, **kwargs)).strip()

    # sublime.error_message() always displays its content in the console
    if error:
        print("YouTubeEditor:")
        return sublime.error_message(msg)

    # Send output to the console if this is a regular log or message dialog;
    # when logging to the panel, we don't want to redundantly log to the
    # console as well.
    if not panel:
        for line in msg.splitlines():
            print("YouTubeEditor: {msg}".format(msg=line))

    if dialog:
        sublime.message_dialog(msg)

    if panel:
        # Output to the panel in all windows
        for window in sublime.windows():
            view = window.find_output_panel("youtubeeditor")
            view.run_command("append", {
                "characters": msg + "\n",
                "force": True,
                "scroll_to_end": True})

        if display:
            display_output_panel()


###----------------------------------------------------------------------------


def copy_video_link(link_url, title=None):
    """
    Given a link to a video (possibly at some timecode), copy it to the
    clipboard and also log it to the output panel; a context command in the log
    allows you to open links in your browser.

    If a title is provided, it will be included in the log output.

    This is here and not in utils to stop a circular dependency problem.
    """
    sublime.set_clipboard(link_url)
    sublime.status_message('URL Copied: %s' % link_url)
    log("PKG: Copied link to clipboard: {0}{1}",
        '' if title is None else "'%s': " % title, link_url)


###----------------------------------------------------------------------------


def setup_log_panel(window, src_window=None):
    """
    Set up an output panel for logging into the provided window. When a source
    window is provided, the content of the panel in that window will be copied
    into the newly created panel to syncrhonize them.
    """
    view = window.create_output_panel("youtubeeditor")
    view.set_read_only(True)
    view.settings().set("gutter", False)
    view.settings().set("rulers", [])
    view.settings().set("word_wrap", False)
    view.settings().set("context_menu", "YouTubeLog.sublime-menu")

    if src_window:
        src_view = src_window.find_output_panel("youtubeeditor")
        if src_view:
            text = src_view.substr(sublime.Region(0, len(src_view)))
            view.run_command("append", {
                "characters": text,
                "force": True,
                "scroll_to_end": True
            })


###----------------------------------------------------------------------------


def display_output_panel():
    """
    Display the output panel based on whether or not the user settings indicate
    that the panel is desired.
    """
    window = sublime.active_window()
    if window.active_panel() == 'output.youtubeeditor':
        return

    # True for always, False for Never, number for Always (but autoclose);
    # thus if this is a boolean and it's False, we should leave. Otherwise,
    # we're good.
    show_panel = yte_setting('auto_show_panel')
    if isinstance(show_panel, bool) and show_panel == False:
        return

    # Show the panel, and if desired autoclose it.
    window.run_command("show_panel", {"panel": "output.youtubeeditor"})
    if isinstance(show_panel, bool) == False and isinstance(show_panel, int):
        close_panel_after_delay(window, show_panel * 1000)


###----------------------------------------------------------------------------


def close_panel_after_delay(window, delay):
    """
    After the provided delay, close the SubliNet panel in the window provided.

    This call debounces other calls for the same window within the given delay
    to ensure that if more logs appear, the panel will remain open long enough
    to see them.
    """
    w_id = window.id()

    # If this is the first call for this window, add a new entry to the
    # tracking map; otherwise increment the existing value.
    if w_id not in close_panel_after_delay.map:
        close_panel_after_delay.map[w_id] = 1
    else:
        close_panel_after_delay.map[w_id] += 1

    def close_panel(window):
        # Decrement the call count for this window; if this is not the last
        # call, then we can leave.
        close_panel_after_delay.map[w_id] -= 1
        if close_panel_after_delay.map[w_id] != 0:
            return

        # Stop tracking this window now, and perform the close in it
        del close_panel_after_delay.map[w_id]

        if window.active_panel() == 'output.youtubeeditor':
            window.run_command('hide_panel')

    sublime.set_timeout(lambda: close_panel(window), delay)

close_panel_after_delay.map = {}


###----------------------------------------------------------------------------