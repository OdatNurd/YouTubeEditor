import sublime
import sublime_plugin

import os


from .networking import NetworkManager, Request, stored_credentials_path, log


# TODO:
#  - Maximum title length is 100 characters
#  - Description is max 5000 characters
#  - Hit the keyword in the first few lines and 2-3 times total
#  - The first few lines (how much?) are shown above the fold
#  - Tags is 500 characters long, no more than 30 characters per tag
#  - Tags with spaces may count as having a length + 2 because internally
#    they're wrapped in quotes and that counts against the length
#  - Tags should include brand related and channel tags for more relvance
#


###----------------------------------------------------------------------------


# The layout for a new YouTube editor window
_layout = {
    'cells': [[0, 0, 1, 1], [0, 1, 1, 2], [0, 2, 1, 3]],
    'cols': [0.0, 1.0],
    'rows': [0.0, 0.05, 0.85, 1.0]
}


# Our global network manager object
netManager = None


###----------------------------------------------------------------------------


def plugin_loaded():
    """
    Initialize plugin state.
    """
    global netManager

    netManager = NetworkManager()


def plugin_unloaded():
    global netManager

    if netManager is not None:
        netManager.shutdown()
        netManager = None


###----------------------------------------------------------------------------


class YoutubeRequest():
    """
    This class abstracts away the common portions of using the NetworkManager
    to make requests and get responses back.

    A request can be made via the `request()` method, and the result will
    be automatically directed to a method in the class. The default handler
    is the name of the request preceeded by an underscore.
    """
    auth_req = None
    auth_resp = None

    def run(self, **kwargs):
        if not netManager.is_authorized():
            self.request("authorize", "_internal_auth")
        else:
            self._authorized(self.auth_req, self.auth_resp)

    def _internal_auth(self, request, result):
        self.auth_req = request
        self.auth_resp = result
        self._authorized(self.auth_req, self.auth_resp)

    def request(self, request, handler=None, **kwargs):
        netManager.request(Request(request, handler, **kwargs), self.result)

    def result(self, request, success, result):
        attr = request.handler if success else "_error"
        if not hasattr(self, attr):
            raise RuntimeError("'%s' has no handler for request '%s'" % (
                self.name(), request.name))

        handler = getattr(self, attr)
        handler(request, result)

    def _error(self, request, result):
        log("""
            An error occured while talking to YouTube

            Request: {req}
            Result:  {err}
            """, error=True, req=request.name, err=result)

    # Assume that most commands want to only enable themselves when there are
    # credentials; commands that are responsible for obtaining credentials
    # override this method.
    def is_enabled(self, **kwargs):
        return netManager.has_credentials()


###----------------------------------------------------------------------------


class YoutubeEditorAuthorizeCommand(YoutubeRequest, sublime_plugin.ApplicationCommand):
    """
    If there are not any cached credentials for the user's YouTube account,
    trigger a request to authorize the plugin to be able to access the account.
    """
    def run(self):
        self.request("authorize")

    def _authorize(self, request, result):
        log("""
            Logged into YouTube

            You are now logged into YouTube! You login credentials
            are cached and will be re-used as needed; Log out to
            clear your credentials or to access a different YouTube
            account.
            """, dialog=True)

    def is_enabled(self):
        return not netManager.has_credentials()


###----------------------------------------------------------------------------


class YoutubeEditorLogoutCommand(YoutubeRequest, sublime_plugin.ApplicationCommand):
    """
    If there are any cached credentials for the user's YouTube account,
    remove them. This will require that the user authenticate the app again
    in order to continue using it.
    """
    def run(self, force=False):
        if not force:
            msg = "If you proceed, you will need to re-authenticate. Continue?"
            if sublime.yes_no_cancel_dialog(msg) == sublime.DIALOG_YES:
                sublime.run_command("youtube_editor_logout", {"force": True})

            return

        self.request("deauthorize")

    def _deauthorize(self, request, result):
        log("""
            Logged out of YouTube.

            Your stored credentials have been cleared; further
            access to YouTube will require you to re-authorize
            YouTuberizer.
            """, dialog=True)


###----------------------------------------------------------------------------


class YoutubeEditorListVideosCommand(YoutubeRequest, sublime_plugin.ApplicationCommand):
    """
    Generate a list of videos for a user's YouTube channel into a new view
    in the currently active window. This will use cached credentials if there
    are any, and ask the user to log in if not.
    """
    def _authorized(self, request, result):
        self.request("uploads_playlist")

    def _uploads_playlist(self, request, result):
        self.request("playlist_contents", playlist_id=result)

    def _playlist_contents(self, request, result):
        window = sublime.active_window()
        items = [[video['title'], video['link']] for video in result]
        window.show_quick_panel(items, lambda i: self.select_video(i, items))

    def select_video(self, idx, items):
        if idx >= 0:
            video = items[idx]
            sublime.set_clipboard(video[1])
            sublime.status_message('URL Copied: %s' % video[0])


###----------------------------------------------------------------------------


class YoutubeEditorVideoDetailsCommand(YoutubeRequest, sublime_plugin.ApplicationCommand):
    """
    Prompt for a video and then open an editor window on its details.
    """
    def _authorized(self, request, result):
        self.request("uploads_playlist")

    def _uploads_playlist(self, request, result):
        self.request("playlist_contents", playlist_id=result)

    def _playlist_contents(self, request, result):
        window = sublime.active_window()
        items = [[video['title'], video['link']] for video in result]
        window.show_quick_panel(items, lambda i: self.select_video(i, items))

    def _video_details(self, request, result):
        sublime.active_window().run_command('youtube_editor_new_window', {
            'video_id': result["video_id"],
            'title': result["title"],
            'body': result["description"],
            'tags': result["tags"]
            })

    def select_video(self, idx, items):
        if idx >= 0:
            video = items[idx]
            video_id = video[1].split('/')[-1]
            self.request("video_details", video_id=video_id)


###----------------------------------------------------------------------------


class YoutubeEditorNewWindowCommand(sublime_plugin.WindowCommand):
    """
    Create a new window for creating a YouTube video description into; the
    window is split horizontally three times to give a title, body and tags
    area.
    """
    def run(self, video_id=None, title='', body='', tags=[]):
        if isinstance(tags, str):
            tags = [tags]

        self.window.run_command('new_window')

        new_window = sublime.active_window()
        new_window.set_tabs_visible(False)
        new_window.set_layout(_layout)

        new_window.settings().set("_yte_youtube_window", True)
        if video_id is not None:
            new_window.settings().set("_yte_video_id", video_id)

        details = [
            {
                'syntax':  'YouTubeTitle',
                'setting': '_yte_video_title',
                'body':    title
            },
            {
                'syntax':  'YouTubeBody',
                'setting': '_yte_video_body',
                'body':    body
            },
            {
                'syntax':  'YouTubeTags',
                'setting': '_yte_video_tags',
                'body':    ','.join(tags)
            }
        ]

        for group, info in reversed(list(enumerate(details))):
            new_window.focus_group(group)
            view = new_window.new_file(syntax='Packages/YouTubeEditor/resources/syntax/%s.sublime-syntax' % info["syntax"])
            view.set_scratch(True)
            view.settings().set(info["setting"], True)
            view.settings().set('youtube_view', True)
            view.run_command('append', {'characters': info["body"]})


## ----------------------------------------------------------------------------


class YoutubeEditorNextView(sublime_plugin.WindowCommand):
    """
    Jump to the next or previous view in a YouTube window; only active in  one
    of the special YouTube views in the window (enforced via a context and not
    here).
    """
    def run(self, prev=False):
        active = self.window.active_group()
        active = ((active + (3 - 1)) if prev else  (active + 1)) % 3

        self.window.focus_group(active)


## ----------------------------------------------------------------------------
