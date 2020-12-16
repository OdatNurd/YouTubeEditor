import sublime

from .logging import log
from .request import Request
from .dotty import dotty
from .utils import yte_setting, BusySpinner

from threading import Thread
import queue

import os
import json

# A compatible version of this is available in hashlib in more recent builds of
# Python, but it takes keyword only arguments. You can swap to that one by
# modifying the call site as appropriate.
from pyscrypt import hash as scrypt
import pyaes

import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow

# TODO: Fields in request results (for example 'tags') don't seem to be
#       mandatory, so we should probably be smarter about that.


###----------------------------------------------------------------------------


# This OAuth 2.0 access scope allows for read-only access to the authenticated
# user's account, but not other types of account access.
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

# The PBKDF Salt value; it needs to be in bytes.
_PBKDF_Salt = "YouTubeEditorSaltValue".encode()

# The encoded password; later the user will be prompted for this on the fly,
# but for expediency in testing the password is currently hard coded.
_PBKDF_Key = scrypt("password".encode(), _PBKDF_Salt, 1024, 1, 1, 32)


###----------------------------------------------------------------------------


def app_client_config():
    """
    Obtain the necessary information to conduct OAuth interactions with the
    YouTube data API.
    """
    if hasattr(app_client_config, "config"):
        return app_client_config.config

    installed = {}
    for key in ("client_id", "client_secret", "auth_uri", "token_uri"):
        installed[key] = yte_setting(key)

    app_client_config.config = {"installed": installed}

    return app_client_config.config


def stored_credentials_path():
    """
    Obtain the cached credentials path, which is stored in the Cache folder of
    the User's configuration information.
    """
    if hasattr(stored_credentials_path, "path"):
        return stored_credentials_path.path

    path = os.path.join(sublime.cache_path(), "YouTubeEditor.credentials")
    stored_credentials_path.path = os.path.normpath(path)

    return stored_credentials_path.path


def cache_credentials(credentials):
    """
    Given a credentials object, cache the given credentials into a file in the
    Cache directory for later use.
    """
    cache_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "id_token": credentials.id_token
    }

    # Encrypt the cache data using our key and write it out as bytes.
    aes = pyaes.AESModeOfOperationCTR(_PBKDF_Key)
    cache_data = aes.encrypt(json.dumps(cache_data, indent=4))

    with open(stored_credentials_path(), "wb") as handle:
        handle.write(cache_data)


def get_cached_credentials():
    """
    Fetch the cached credentials from a previous operation; this will return
    None if there is currently no cached credentials. This will currently
    raise an exception if the file is broken (so don't break it).
    """
    try:
        # Decrypt the data with the key and convert it back to JSON.
        with open(stored_credentials_path(), "rb") as handle:
            aes = pyaes.AESModeOfOperationCTR(_PBKDF_Key)
            cache_data = aes.decrypt(handle.read()).decode("utf-8")

            cached = json.loads(cache_data)

    except FileNotFoundError:
        return None

    client_config = app_client_config()
    return google.oauth2.credentials.Credentials(
        cached["token"],
        cached["refresh_token"],
        cached["id_token"],
        client_config["installed"]["token_uri"],
        client_config["installed"]["client_id"],
        client_config["installed"]["client_secret"],
        SCOPES
    )


# Authorize the request and store authorization credentials.
def get_authenticated_service():
    """
    This builds the appropriate endpoint object to talk to the YouTube data
    API, using a combination of the client secrets file and either cached
    credentials or asking the user to log in first.

    If there is no cached credentials, or if they are not valid, then the user
    is asked to log in again before this returns.

    The result is an object that can be used to make requests to the API.
    This fetches the authenticated service for use
    """
    credentials = get_cached_credentials()
    if credentials is None or not credentials.valid:
        # TODO: This can raise exceptions, AccessDeniedError
        flow = InstalledAppFlow.from_client_config(app_client_config(), SCOPES)
        credentials = flow.run_local_server(client_type="installed",
            authorization_prompt_message='YouTubeEditor: Launching browser to log in',
            success_message='YouTubeEditor login complete! You can close this window.')

        cache_credentials(credentials)

    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


###----------------------------------------------------------------------------



class NetworkThread(Thread):
    """
    The background thread that is responsible for doing all of network
    operations. All of the state is kept in this thread; requests are added in
    and callbacks are used to signal results out.
    """
    def __init__(self, event, queue):
        # log("== Creating network thread")
        super().__init__()
        self.event = event
        self.requests = queue
        self.youtube = None

        # Set up the cache data structure
        self._init_cache()

        # The requests that we know how to service, and what method invokes
        # them.
        self.request_map = {
            "authorize": self.authenticate,
            "deauthorize": self.deauthenticate,
            "channel_details": self.channel_details,
            "channel_list": self.channel_list,
            "playlist_contents": self.playlist_contents,
            "playlist_list": self.playlist_list,
            "video_details": self.video_details
        }

    def _init_cache(self):
        """
        Set up our internal cache object to be empty and ready to track the
        results of our data requests.
        """
        # This dictionary contains a cache of the data that has been requested
        # during this session; requests that ask for data already in the cache
        # will retreive that data immediately with no further requests being
        # made unless they request a refresh.
        self.cache = dotty({
            # The information on fetched channel information; this is a list of
            # all channels associated with the currently authenticated user.
            # "channel_list": []

            # The information on fetched channel details; this object is keyed
            # on channel ID's, with the value being the details for that
            # channel.
            "channel_details": {}
        })

    # def __del__(self):
    #     log("== Destroying network thread")

    def validate(self, request, required=None, any_of=None):
        """
        Takes an incoming request and optional sets of required and optional
        arguments for that request.

        All arguments in required must appear in the request, and at least one
        of any_of; if this is not the case, it's an error. Either set can be
        None to indicate that there are no required or semi-optional arguments.
        """
        args = set(request)

        if required and not required.issubset(args):
            raise ValueError("missing required arguments: {}".format(
                ", ".join(required - args)))

        if any_of and not args & any_of:
            raise ValueError("arguments require at least one of: {}".format(
                ", ".join(any_of)))

    def authenticate(self, request):
        """
        Start the authorization flow. If the user has never authorized the app,
        this will launch a browser to ask them to do so and will return a
        result as appropriate. Otherwise it will used cached credentials.

        TODO: This can theoretically block forever; this should do something
        like spawn a temporary thread so that it could cancel after a timeout
        or on user request.
        """
        log("THR: Requesting authorization")
        self.youtube = get_authenticated_service()
        return "Authenticated"

    def deauthenticate(self, request):
        """
        Completely de-authenticate the current user; this will remove the
        current login credentials that are cached (if any) and also discard the
        current service object.
        """
        log("THR: Removing stored login credentials")
        try:
            self.youtube = None
            self._init_cache()
            os.remove(stored_credentials_path())
        except:
            pass

        return "Deauthenticated"

    def channel_details(self, request):
        """
        Given a channel ID, obtain the specifics about that particular channel.
        """
        self.validate(request, {"channel_id"})
        log("API: Fetching channel details for channel {0}", request["channel_id"])

        channel_id = request["channel_id"]

        if channel_id in self.cache['channel_details']:
            if request["refresh"]:
                log("DBG: Clearing Channel Cache (in ID)")
                del self.cache["channel_list"]
            else:
                log("DBG: Returning cached data (in ID)")
                return self.cache["channel_details"][channel_id]
        else:
            log("DBG: Cache miss on channel data (in ID)")

        self.channel_list(Request("channel_list"))
        if channel_id in self.cache["channel_details"]:
            return self.cache["channel_details"][channel_id]

        raise KeyError("No channel with id {} found".format(channel_id))

    def channel_list(self, request):
        """
        Obtain details about the channels that are associated with the
        currently authenticated user.
        """
        log("API: Fetching channel details")

        if "channel_list" in self.cache:
            if request["refresh"]:
                log("DBG: Clearing Channel Cache")
                del self.cache["channel_list"]
            else:
                log("DBG: Returning cached data")
                return self.cache["channel_list"]
        else:
            log("DBG: Cache miss on channel data")

        # Request breakdown is as follows. Note that snippet and
        # brandingSettings have overlap between them, but each has information
        # that the other does not.
        #
        # id:               the unique channel ID
        # snippet:          basic channel details (title, thumbnails, etc)
        # brandingSettings: channel branding (title, description, etc)
        # contentDetails:   uploaded and liked video playlist ID's
        # statistics:       channel views, video counts, etc
        # status            privacy status, upload abilities, etc
        response = self.youtube.channels().list(
            mine=True,
            part='id,snippet,brandingSettings,contentDetails,statistics,status'
        ).execute()

        if "items" not in response or not response["items"]:
            raise KeyError("No channels available for the current user")

        result = [dotty(channel) for channel in response["items"]]
        log("API: Retreived information for {0} channel(s):", len(result))
        log("API: Channels: {0}", str([c['brandingSettings.channel.title'] for c in result]))
        log("API: Channels: Public video count: {0}", str([c['statistics.videoCount'] for c in result]))

        self.cache["channel_list"] = result
        for channel in result:
            self.cache["channel_details"][channel["id"]] = channel

        log("DBG: Cached channel response")

        return result

    def playlist_list(self, request):
        """
        Obtain information on the playlists that are defined for the channel
        with the ID provided.
        """
        self.validate(request, {"channel_id"})
        log("API: Fetching playlists for channel: {0}", request["channel_id"])

        # Request breakdown is as follows.
        #
        # id:              the unique playlist ID
        # contentDetails:  the number of items contained in the playlist
        # snippet:         basic playlist details (title, description, etc)
        # status:          privacy status
        list_request = self.youtube.playlists().list(
            channelId=request["channel_id"],
            part="id,snippet,contentDetails,status",
            maxResults=50
        )

        # This is an example of a paged request that will keep executing going
        # through pages until all information is captured; you could also do
        # this piecemeal if needed.
        results = []
        while list_request:
            response = list_request.execute()

            # Grab information about each playlist.
            for playlist in response['items']:
                results.append(dotty(playlist))

            list_request = self.youtube.playlistItems().list_next(
                list_request, response)

        log("API: Found {0} playlists", len(results))
        return results

    def playlist_contents(self, request):
        """
        Obtain information on the contents of a specific playlist, given by
        ID. This can fetch either simple details or more detailed information.
        The more detailed information requires two queries, one to fetch just
        video ID and another to fetch details.

        This is because the standard parts allows in the playlist item query
        does not include video details like view count and such, which are not
        always relevant.
        """
        self.validate(request, {"playlist_id"})
        log("API: Fetching playlist contents for playlist: {0}", request["playlist_id"])

        # Request breakdown is as follows. Note that snippet and contentDetails
        # have overlap between them, but each has information that the other
        # does not.
        #
        # id:               the unique item ID (**NOTE** this is NOT video ID!)
        # snippet:          basic video details (title, description, etc)
        # contentDetails:   video id and publish time
        # status            privacy status
        if request["full_details"]:
            part = "contentDetails"
        else:
            part = request["part"] or 'id,snippet,contentDetails,status'

        list_request = self.youtube.playlistItems().list(
            playlistId=request["playlist_id"],
            part=part,
            maxResults=50
        )

        # This is an example of a paged request that will keep executing going
        # through pages until all information is captured; you could also do
        # this piecemeal if needed.
        results = []
        while list_request:
            response = list_request.execute()

            # Grab information about each video.
            for playlist_item in response['items']:
                results.append(dotty(playlist_item))

            list_request = self.youtube.playlistItems().list_next(
                list_request, response)

        log("API: Playlist contains {0} items", len(results))

        # If we're doing a full details, then all we actually gathered is a
        # list of video ID's and we need a separate request in order to
        # actually get the full details of the video.
        if request["full_details"]:
            log("API: Fetching video details for playlist contents")
            part = request["part"] or 'id,snippet,contentDetails,status'

            # This request gets angry if you give is a list of more than 50
            # items, and it also gets angry if you try to page it (as above);
            # this seems to be undocumented, but it looks like we need to do
            # the batching ourselves.
            ids = [v['contentDetails.videoId'] for v in results]
            id_list = [ids[i * 50:(i + 1) * 50] for i in range((len(ids) + 50 - 1) // 50 )]
            results = []

            # TODO: The list of things we ask for here could perhaps be
            # constrained; for list purposes we might not need all details,
            # only things we want to display in the quick panel.
            for sublist in id_list:
                response = self.youtube.videos().list(
                    id=sublist,
                    part=part
                    ).execute()

                for video in response["items"]:
                    results.append(dotty(video))

        return results

    def video_details(self, request):
        """
        Given the ID of a video for a user, fetch the details for that video
        for editing purposes.
        """
        self.validate(request, {"video_id"})
        log("API: Fetching video details for: {0}", request["video_id"])

        # Request breakdown is as follows. Note that snippet and contentDetails
        # have overlap between them, but each has information that the other
        # does not.
        #
        # snippet:          basic video details (title, description, etc)
        # contentDetails:   content detais (publish time, duration, etc)
        # status:           video status (uploaded, processed, private, etc)
        # statistics:       statistics (views, likes, dislikes, etc)
        part = request["part"] or 'snippet,contentDetails,status,statistics'
        response = self.youtube.videos().list(
            id=request["video_id"],
            part=part
            ).execute()

        for item in response['items']:
            result = dotty(item)
            log("API: Got information for: {0}", result['snippet.title'])
            return result

        return None

    def handle_request(self, request_obj):
        """
        Handle the asked for request, dispatching an appropriate callback when
        the request is complete (depending on whether it worked or not).
        """
        request = request_obj["request"]
        callback = request_obj["callback"]

        success = False
        result = None

        with BusySpinner(request.reason):
            try:
                handler = self.request_map.get(request.name, None)
                if handler is None:
                    raise ValueError("Unknown request '%s'" % request.name)

                result = handler(request)
                success = True

            except HttpError as err:
                result = dotty(json.loads(err.content.decode('utf-8')))

            except Exception as err:
                result = dotty({"error": {"code": -1, "message": str(err) } })

        sublime.set_timeout(lambda: callback(success, result))
        self.requests.task_done()

    def run(self):
        """
        The main loop needs to loop until a semaphore tells it that it's time
        to quit, at which point it will drop out of the loop and gracefully
        exit, perhaps telling all connections to close in response.

        This needs to select all connections for reading, only those that have
        data pending send for writing, and needs to safely busy loop when there
        are no connections.
        """
        # log("== Entering network loop")
        while not self.event.is_set():
            try:
                request = self.requests.get(block=True, timeout=0.25)
                self.handle_request(request)

            except queue.Empty:
                pass

        log("THR: YouTube thread has terminated")


###----------------------------------------------------------------------------
