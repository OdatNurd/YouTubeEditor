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
        h1 span {{
            font-size: 0.80rem;
            position: relative;
            left: 0;
        }}
        .private {{
            color: var(--redish);
        }}
        .public {{
            color: var(--greenish);
        }}
        .unlisted {{
            color: var(--yellowish);
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
        .tags {{
            width: 40rem;
            margin: 0;
            padding: 0;
            border-top: 1px solid var(--greenish);
            color: color(var(--greenish) alpha(0.7));
            font-size: 0.9rem;
        }}
        .commands {{
            width: 40rem;
            margin: 0;
            padding: 0;
            border-top: 1px solid var(--greenish);
            color: color(var(--greenish) alpha(0.7));
            font-size: 0.9rem;
        }}
     </style>
     {body}
</body>
"""

_body = """
<h1>{title} <span class="{vis_class}">({visibility})</span></h1>
<div class="statistics">
    <span class="viewcount">{views} views</span>
    <span class="likes">✔:{likes}</span>
    <span class="dislikes">✘:{dislikes}</span>
</div>
<p class="description">{description}</p>
<div class="tags">{tags}</div>
<div class="commands">
  [ <a href="subl:youtube_editor_view_video_link {{&quot;video_id&quot;:&quot;{video_id}&quot;}}">Watch</a> ]
  [ <a href="subl:echo {{&quot;video_id&quot;:&quot;{video_id}&quot;}}">Get Link</a> ]
  [ <a href="subl:echo {{&quot;video_id&quot;:&quot;{video_id}&quot;}}">Edit</a> ]
  [ <a href="subl:youtube_editor_edit_in_studio {{&quot;video_id&quot;:&quot;{video_id}&quot;}}">Edit in Studio</a> ]
</div>
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
            vis_class=video['status.privacyStatus'],
            visibility=video['status.privacyStatus'].title(),
            views=video['statistics.viewCount'],
            likes=video['statistics.likeCount'],
            dislikes=video['statistics.dislikeCount'],
            description=video['snippet.description'].split('\n', 1)[0],
            tags=", ".join(video.get("snippet.tags", [])),
            video_id=video['id']
            )
    )


    view.show_popup(content,
        flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
        location=point,
        max_width=1024,
        max_height=1024)


###----------------------------------------------------------------------------

