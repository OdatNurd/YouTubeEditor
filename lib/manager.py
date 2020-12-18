from .logging import log
from .networking import NetworkThread, stored_credentials_path

from threading import Event, Lock
import queue

import os


###----------------------------------------------------------------------------


class NetworkManager():
    """
    This class manages all of our network interactions by using a background
    thread (or threads) to make requests, handing results back as they are
    obtained and signalling other events.

    There should be a single global instance of this class created; it connects
    the network data gathering with the Sublime front end.
    """
    def __init__(self):
        self.thr_event = Event()
        self.request_queue = queue.Queue()
        self.net_thread = NetworkThread(self.thr_event, self.request_queue)
        self.authorized = False

    def startup(self):
        """
        Start up the networking system; this initializes and starts up the
        network thread.

        This can be called just prior to the first network operation;
        optionally it can also be invoked from plugin_loaded().
        """
        log("PKG: Launching YouTube thread")
        self.net_thread.start()

    def shutdown(self):
        """
        Shut down the networking system; this shuts down any background threads
        that may be running. This should be called from plugin_unloaded() to do
        cleanup before we go away.
        """
        if self.net_thread.is_alive():
            log("PKG: Terminating YouTube thread")
            self.thr_event.set()
            self.net_thread.join(0.25)

    def has_credentials(self):
        """
        Returns an indication of whether or not there are currently stored
        credentials for a YouTube login; this indicates that the user has
        already authorized the application to access their account.
        """
        return os.path.isfile(stored_credentials_path())

    def is_authorized(self):
        """
        Determine if the plugin is currently authorized or not; this
        is an indication that data requests can be made; prior to this point
        requests will fail.
        """
        return self.authorized

    def callback(self, request, user_callback, success, result):
        """
        This callback is what is submitted to the network thread to invoke
        when a result is delivered. We get the success and the result, as
        well as the request that was made and the user callback.

        NOTE: The NetworkThread always invokes this in Sublime's main thread,
        not from within itself; this is the barrier where the requested data
        shifts between threads.
        """
        if request.name == "authorize":
            self.authorized = success
        elif request.name == "deauthorize":
            self.authorized = False

        user_callback(request, success, result)

    def request(self, request, callback, refresh=False):
        """
        Submit the given request to the network thread; the thread will execute
        the task and then invoke the callback once complete; the callback gets
        called with a boolean that indicates the success or failure, and either
        the error reason (on fail) or the result (on success).

        Internally this class will cache the result of some requests; in order
        to force a re-request, set refresh to True.
        """
        if not self.net_thread.is_alive():
            self.startup()

        self.request_queue.put({
            "request": request,
            "callback": lambda s, r: self.callback(request, callback, s, r)
        })



###----------------------------------------------------------------------------
