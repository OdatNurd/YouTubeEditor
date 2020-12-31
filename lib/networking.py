import sublime

from .logging import log
from .request import Request
from . import dotty
from .utils import yte_setting, BusySpinner

from threading import Thread
import queue

import os
import json
import traceback

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


# This OAuth 2.0 access scope allows for read-write access to the authenticated
# user's account, allowing the app to do anything the user could do on the
# YouTube site.
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

# The PBKDF Salt value; it needs to be in bytes.
_PBKDF_Salt = "YouTubeEditorSaltValue".encode()

# The encoded password; later the user will be prompted for this on the fly,
# but for expediency in testing the password is currently hard coded.
_PBKDF_Key = scrypt("password".encode(), _PBKDF_Salt, 1024, 1, 1, 32)

# When using the set_video_details request, new video details need to be
# provided for the update. The request itself allows you to provide a full
# video details dictionary, but YouTube only allows certain keys to be present
# or it will generate a 500 error (at least sometimes).
#
# Hence, we need to filter the incoming request to only those fields that
# YouTube will allow to be updated.  This represents the structure that's
# allowed to be modified; the top level keys are keys that can be present.
#
# The value of each key is either a set that indicates what fields are allowed
# or, for values that are not themselves dictionaries, the value is a boolean.
#
# The filter will constrain what you provide to fit with this, though you don't
# need to provide all the keys here.
_set_video_keys = {
    # The ID value is required in the input so that the API knows what video
    # it is that you're trying to update.
    "id": True,

    # When updating the snippet, the title and categoryId values are mandatory
    # as a part of the update.
    "snippet": {
        "title", "description", "tags", "categoryId", "defaultLanguage"
    },

    # When setting publishAt, you must also set privacyStatus to "private" to
    # schedule the video to be published at that point.
    "status": {
        "embeddable", "license", "privacyStatus", "publicStatsViewable",
        "publishAt", "selfDeclaredMadeForKids"
    },

    "recordingDetails": { "recordingDate" },

    # Localizations are also allowed, but we're not filtering them here because
    # internationalization is butts.
    "localizations": True
}


###----------------------------------------------------------------------------


class DottyEncoder(json.JSONEncoder):
    """
    A simple custom JSON Encoder that knows how to encode a dotty dictionary
    by returning the original wrapped dictionary.
    """
    def default(self, o):
        if isinstance(o, dotty.Dotty):
            return o.to_dict()

        return json.JSONEncoder.default(self, o)


###----------------------------------------------------------------------------


def filter_new_video_details(details):
    """
    Given a video data dictionary as might be provided by a request for video
    details, filter the keys in it to those which are allowed to be set via the
    API in the set_video_details network request. The result is suitable for
    being used to perform an update.

    Note however that the restrictions put in place by the API still apply; not
    providing a key that has a value already will make YouTube delete that
    property (that is, this just makes the request formally correct and doesn't
    guarantee that it will do what you want).
    """
    new_details = {}
    for key in _set_video_keys:
        if key not in details:
            continue

        if isinstance(_set_video_keys[key], bool):
            new_details[key] = details[key]
            continue

        subkeys = _set_video_keys[key] & set(details[key].keys())
        new_details[key] = {k: details[key][k] for k in subkeys}

    return new_details


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


def stored_cache_path():
    """
    Obtain the data request cache file path, which is stored in the Cache
    folder of the User's configuration information.
    """
    if hasattr(stored_cache_path, "path"):
        return stored_cache_path.path

    path = os.path.join(sublime.cache_path(), "YouTubeEditorCacheData.json")
    stored_cache_path.path = os.path.normpath(path)

    return stored_cache_path.path


def load_cached_request_data():
    """
    Decrypt and return back a dict that represents saved cache data from a
    previous run. This will return None if there is currently no cached data
    present. This will currently raise an exception if the file is broken (so
    don't break it).
    """
    if not yte_setting('cache_downloaded_data'):
        return None

    with BusySpinner('Loading YouTubeEditor cache data', time=True):
        try:
            # Decrypt the data with the key and convert it back to JSON.
            with open(stored_cache_path(), "rb") as handle:
                raw_data = handle.read()

                if yte_setting('encrypt_cache'):
                    aes = pyaes.AESModeOfOperationCTR(_PBKDF_Key)
                    cache_data = aes.decrypt(raw_data).decode("utf-8")
                else:
                    cache_data = raw_data.decode("utf-8")

                return json.loads(cache_data, object_hook=dotty.dotty)

        except FileNotFoundError:
            return None


def save_cached_request_data(cache_data):
    """
    Given a cache data object, write it into an encrypted file for later
    use in another session.
    """
    if not yte_setting('cache_downloaded_data'):
        return

    # Encrypt the cache data using our key and write it out as bytes.
    with BusySpinner('Updating data cache', time=True):
        json_data = json.dumps(cache_data, cls=DottyEncoder)

        if yte_setting('encrypt_cache'):
            aes = pyaes.AESModeOfOperationCTR(_PBKDF_Key)
            cache_data = aes.encrypt(json_data)
        else:
            cache_data = json_data.encode("utf-8")

        with open(stored_cache_path(), "wb") as handle:
            handle.write(cache_data)


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
    cache_data = aes.encrypt(json.dumps(cache_data))

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

        # Set up the cache data structure when the thread launches, since the
        # load of the cached data can actually take a fair bit of time and we
        # don't want to hang the load of the plugin by doing it in the main
        # thread.
        self.cache = None

        # The requests that we know how to service, and what method invokes
        # them.
        self.request_map = {
            "authorize": self.authenticate,
            "deauthorize": self.deauthenticate,
            "flush_cache": self.flush_cache,
            "channel_details": self.channel_details,
            "channel_list": self.channel_list,
            "playlist_contents": self.playlist_contents,
            "playlist_list": self.playlist_list,
            "video_details": self.video_details,
            "set_video_details": self.set_video_details
        }

    # def __del__(self):
    #     log("== Destroying network thread")

    def _init_cache(self):
        """
        Set up our internal cache object to be empty and ready to track the
        results of our data requests.
        """
        # This dictionary contains a cache of the data that has been requested
        # during this session; requests that ask for data already in the cache
        # will retreive that data immediately with no further requests being
        # made unless they request a refresh.
        self.cache = load_cached_request_data() or dotty.dotty({
            # The information on fetched channel information; this is a list of
            # all channels associated with the currently authenticated user.
            "channel_list": [],

            # The information on fetched channel details; this object is keyed
            # on channel ID's, with the value being the details for that
            # channel.
            "channel_details": dotty.dotty({}),

            # The information on fetched playlists; this object is keyed on
            # channel ID's, with the value being a list of all playlists that
            # appear on that channel
            "playlist_list": dotty.dotty({}),

            # The information on the contents of fetched playlists; this object
            # is keyed on playlist ID's, with the value being a list of the
            # playlist contents.
            "playlist_contents": dotty.dotty({}),

            # The information on videos stored in playlists. This object is
            # keyed on video ID, with the values being the information on that
            # video. This is only data considered relevant for the purposes of
            # displaying the playlist (i.e. it is not guaranteed to be full
            # video details).
            "playlist_videos": dotty.dotty({}),

            # The information on fetched videos; this object is keys on video
            # ID's, with the value being the details of that particular video.
            "video_details": dotty.dotty({})
        })

    def _fetch_video_details(self, video_ids, part, cache_data):
        """
        Fetch video details for the video(s) provided, and update the given
        cache_data with the results. cache_data is a dictionary whose keys are
        video ids and whose values are the details for those videos. In use
        any videos submitted for lookup that appear in the cache already will
        be skipped, and any that are looked up will be added to the cache.

        The provided video_ids can be either a single string video ID or a list
        of ID's to look up. The given part is used to determine what
        information gets looked up

        The returned value is a list of video details for each given video
        ID.
        """
        missing_ids = [vid for vid in video_ids if vid not in cache_data]

        log("API: Fetching video details ({0} cached, fetching {1} of {2})",
            len(video_ids) - len(missing_ids), len(missing_ids), len(video_ids));

        # This request seems to top out at 50 requested items, so chunk the list
        # so we can batch it, since it doesn't support native paging (since it
        # is not a traditional list query, one assumes).
        id_list = [missing_ids[i * 50:(i + 1) * 50] for i in range((len(missing_ids) + 50 - 1) // 50 )]

        for sublist in id_list:
            response = self.youtube.videos().list(
                id=sublist,
                part=part
                ).execute()

            for v in response["items"]:
                video = dotty.dotty(v)
                cache_data[v['id']] = video

        return [cache_data[vid] for vid in video_ids]


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

            os.remove(stored_credentials_path())
            os.remove(stored_cache_path())
            self._init_cache()

        except:
            pass

        return "Deauthenticated"

    def flush_cache(self, request):
        """
        Flush away any cached information from previously made requests. Once
        this is done, any requests made will have to perform a full request
        again.
        """
        log("THR: Requesting Cache Flush")
        try:
            os.remove(stored_cache_path())
        except:
            pass

        self._init_cache()
        return "Flushed"

    def channel_details(self, request):
        """
        Given a channel ID, obtain the specifics about that particular channel.
        """
        self.validate(request, {"channel_id"})
        log("API: Fetching channel details for channel {0}", request["channel_id"])

        channel_id = request["channel_id"]

        if channel_id in self.cache['channel_details']:
            if request["refresh"]:
                self.cache["channel_list"] = []
            else:
                return self.cache["channel_details"][channel_id]

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

        if "channel_list" in self.cache and self.cache["channel_list"]:
            if request["refresh"]:
                self.cache["channel_list"] = []
            else:
                return self.cache["channel_list"]

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

        result = [dotty.dotty(channel) for channel in response["items"]]
        log("API: Retreived information for {0} channel(s):", len(result))
        log("API: Channels: {0}", str([c['brandingSettings.channel.title'] for c in result]))
        log("API: Channels: Public video count: {0}", str([c['statistics.videoCount'] for c in result]))

        self.cache["channel_list"] = result
        for channel in result:
            self.cache["channel_details"][channel["id"]] = channel

        save_cached_request_data(self.cache)

        return result

    def playlist_list(self, request):
        """
        Obtain information on the playlists that are defined for the channel
        with the ID provided.
        """
        self.validate(request, {"channel_id"})
        channel_id = request["channel_id"]

        log("API: Fetching playlists for channel: {0}", channel_id)

        if channel_id in self.cache["playlist_list"]:
            if request["refresh"]:
                del self.cache["playlist_list"][channel_id]
            else:
                return self.cache["playlist_list"][channel_id]

        # Request breakdown is as follows.
        #
        # id:              the unique playlist ID
        # contentDetails:  the number of items contained in the playlist
        # snippet:         basic playlist details (title, description, etc)
        # status:          privacy status
        list_request = self.youtube.playlists().list(
            channelId=channel_id,
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
                results.append(dotty.dotty(playlist))

            list_request = self.youtube.playlistItems().list_next(
                list_request, response)

        log("API: Found {0} playlists", len(results))

        self.cache["playlist_list"][channel_id] = results

        save_cached_request_data(self.cache)

        return results

    def playlist_contents(self, request):
        """
        Obtain information on the contents of a specific playlist, given by
        ID. This returns a list of the videos in the playlist, complete with
        all of their details.
        """
        self.validate(request, {"playlist_id"})
        playlist_id = request["playlist_id"]

        log("API: Fetching playlist contents for playlist: {0}", playlist_id)

        if playlist_id in self.cache['playlist_contents']:
            if request["refresh"]:
                del self.cache["playlist_contents"][playlist_id]

                # TODO: This clobbers playlist video details for every possible
                #       video; should it only clobber videos that appear in the
                #       playlist we're re-fetching instead?
                self.cache["playlist_videos"] = {}
            else:
                return self.cache["playlist_contents"][playlist_id]

        # Request breakdown is as follows. Note that snippet and contentDetails
        # have overlap between them, but each has information that the other
        # does not.
        #
        # id:               the unique item ID (**NOTE** this is NOT video ID!)
        # snippet:          basic video details (title, description, etc)
        # contentDetails:   video id and publish time
        # status            privacy status of the video
        list_request = self.youtube.playlistItems().list(
            playlistId=request["playlist_id"],
            part="contentDetails",
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
                results.append(dotty.dotty(playlist_item))

            list_request = self.youtube.playlistItems().list_next(
                list_request, response)

        log("API: Playlist contains {0} items", len(results))

        # Get the list of all videos contained in the playlist, and fetch down
        # the data, updating the cache as we do. This is smart enough to not
        # re-request information it has previously retreived.
        ids = [v['contentDetails.videoId'] for v in results]
        results = self._fetch_video_details(ids, 'id,snippet,status,statistics', self.cache["playlist_videos"])

        # Cache the results for a future call
        self.cache["playlist_contents"][playlist_id] = results

        save_cached_request_data(self.cache)

        return results

    def video_details(self, request):
        """
        Given one or more video ID's for a video, fetch the details for those
        videos. The results of this are cached separately from the cache used
        for playlist video details, since each fetches a different portion of
        the data available.

        This can handle one or more video lookups, so the result is an array
        of video information as a result.
        """
        self.validate(request, {"video_id"})

        # Get video ID's and ensure that it's a list.
        video_ids = request["video_id"]
        if not isinstance(video_ids, list):
            video_ids = [video_ids]

        log("API: Fetching video details for: {0}", video_ids)

        # If we are asked to refresh, we need to delete from the cache all
        # video IDs we were asked to request that were previously requested.
        # All other caching happens below, in the request and subsequent
        # handling.
        if request["refresh"]:
            for video in video_ids:
                if video in self.cache["video_details"]:
                    del self.cache["video_details"][video]

        # Fetch the details for all requested videos; this will use the cache
        # to only return what's needed.
        result = self._fetch_video_details(video_ids, 'snippet,contentDetails,status,statistics', self.cache["video_details"])
        save_cached_request_data(self.cache)

        return result

    def set_video_details(self, request):
        """
        Given video details, dispatch a request to the YouTube Data API to
        update the data for the given video to those details.

        You must specify a part that says what data you're modifying as well as
        a dictionary that contains the data to be updated, in the same format
        that YouTube provides it to you if you were to ask for the same part.

        Not all properties are mutable; it's safe to provide immutable data
        items and they'll be ignored for the update.

        The result of this request is a video_details result that contains the
        new video data.

        NOTE: Any video information that you don't provide here will be deleted
              from the video on YouTube if it exists; so ensure that what you
              provide this is what you want the data to be.
        """
        self.validate(request, {"part", "video_details"})

        part = request["part"]
        video_details = filter_new_video_details(request["video_details"])

        log("API: Update video details for: {0}", video_details["id"])

        response = self.youtube.videos().update(
            part=part,
            body=video_details
            ).execute()

        new_details = dotty.dotty(response)
        self.cache["video_details"][new_details['id']] = new_details

        save_cached_request_data(self.cache)

        return new_details

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

                # Initialize the cache if it hasn't been done yet.
                if self.cache == None:
                    # These requests don't need the data cache and might
                    # actually invalidate it, so don't waste time loading it
                    # it in if we're just going to clobber it away.
                    if request.name not in ('authorize', 'deauthorize', 'flush_cache'):
                        log("THR: Initializing the data cache")
                        self._init_cache()

                result = handler(request)
                success = True

            except HttpError as err:
                result = dotty.dotty(json.loads(err.content.decode('utf-8')))

            except Exception as err:
                result = dotty.dotty({"error": {"code": -1, "message": str(err) } })

                # Display the trace to the console for diagnostic purposes.
                print(traceback.format_exc())

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
