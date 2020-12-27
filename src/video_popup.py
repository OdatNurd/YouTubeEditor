import sublime
import sublime_plugin


###----------------------------------------------------------------------------


_video_popup = """
<body id="youtubeeditor-video-details">
    <style>
        body {{
            font-family: system;
            margin: 0.5rem 1rem;
            width: 40em;
        }}
        h1 {{
            width: 33em;
            font-size: 1.2rem;
            font-weight: bold;
            margin: 0;
            padding: 0;
            border-bottom: 2px solid var(--bluish);
            color: var(--bluish);
        }}
        .statistics {{
            font-size: 0.8rem;
            line-height: 0.8rem;
            margin-top: -0.8rem;
            position: relative;
        }}
        .viewcount {{
            color: var(--purplish);
        }}
        .likes {{
            color: var(--greenish);
        }}
        .dislikes {{
            color: var(--redish);
        }}
        .description {{
            color: color(var(--foreground) alpha(0.70));
        }}
     </style>
     {body}
</body>
"""

_body = """
<h1>{title}</h1>
<div class="statistics">
    <span class="viewcount">{views} views</span>
    <span class="likes">✔:{likes}</span>
    <span class="dislikes">✘:{dislikes}</span>
</div>
<p class="description">{description}</p>
"""


###----------------------------------------------------------------------------


def show_video_popup(view, point, video):
    """
    At the given point in the given view, display a hover popup for the video
    whose information is provided.

    The hover popup will contain the key information for the video, and also
    contain some links that will trigger commands that can be taken on the
    video as well.
    """
    content = _video_popup.format(
        body=_body.format(
            title=video['snippet.title'],
            views=video['statistics.viewCount'],
            likes=video['statistics.likeCount'],
            dislikes=video['statistics.dislikeCount'],
            description=video['snippet.description'].split('\n', 1)[0]
            )
    )


    view.show_popup(content,
        flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
        location=point,
        max_width=1024,
        max_height=512)


###----------------------------------------------------------------------------
