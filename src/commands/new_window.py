import sublime
import sublime_plugin

from ..core import YoutubeRequest, yte_syntax


###----------------------------------------------------------------------------


# The layout for a new YouTube editor window
_layout = {
    'cells': [[0, 0, 2, 1], [0, 1, 1, 2], [0, 2, 2, 3], [1, 1, 2, 2]],
    'cols': [0.0, 0.6, 1.0],
    'rows': [0.0, 0.05, 0.85, 1.0]
}


###----------------------------------------------------------------------------


class YoutubeEditorNewWindowCommand(sublime_plugin.WindowCommand):
    """
    Create a new window for creating or editing the details for a YouTube
    video. A new window will be created that is split in order to display the
    title, description and tags of the video.

    In addition, appropriate syntaxes are set, tabs are hidden, and other
    changes to window layout are made in order to make the editor as seamless
    as possible.

    The command can optionally also pre-populate the information for any of the
    views, and will mark itself with the video ID as well if one is given.
    """
    def run(self, video_id=None, title='', description='', tags=[]):
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
                'name':    'Video Title',
                'body':    title
            },
            {
                'syntax':  'YouTubeBody',
                'setting': '_yte_video_body',
                'name':    'Video Body',
                'body':    description
            },
            {
                'syntax':  'YouTubeTags',
                'setting': '_yte_video_tags',
                'name':    'Video Tags',
                'body':    ','.join(tags)
            }
        ]

        for group, info in reversed(list(enumerate(details))):
            new_window.focus_group(group)
            view = new_window.new_file(syntax=yte_syntax(info["syntax"]))
            view.set_scratch(True)
            view.set_name(info["name"])
            view.settings().set(info["setting"], True)
            view.settings().set('youtube_view', True)

            view.run_command('append', {'characters': info["body"]})


###----------------------------------------------------------------------------
