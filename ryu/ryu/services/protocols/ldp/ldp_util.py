import socket
import logging
from ryu.lib import hub

LOG = logging.getLogger('ldp_util')

def from_inet_ptoi(bgp_id):
    """Convert an IPv4 address string format to a four byte long.
    """
    four_byte_id = None
    try:
        packed_byte = socket.inet_pton(socket.AF_INET, bgp_id)
        four_byte_id = long(packed_byte.encode('hex'), 16)
    except ValueError:
        LOG.debug('Invalid bgp id given for conversion to integer value %s' %
                  bgp_id)

    return four_byte_id

class Timer(object):
    def __init__(self, handler_):
        assert callable(handler_)

        super(Timer, self).__init__()
        self._handler = handler_
        self._event = hub.Event()
        self._thread = None

    def start(self, interval):
        """interval is in seconds"""
        if self._thread:
            self.cancel()
        self._event.clear()
        self._thread = hub.spawn(self._timer, interval)

    def cancel(self):
        if self._thread is None:
            return
        self._event.set()
        hub.joinall([self._thread])
        self._thread = None

    def is_running(self):
        return self._thread is not None

    def _timer(self, interval):
        # Avoid cancellation during execution of self._callable()
        cancel = self._event.wait(interval)
        if cancel:
            return

        self._handler()

class TimerEventSender(Timer):
    # timeout handler is called by timer thread context.
    # So in order to actual execution context to application's event thread,
    # post the event to the application
    def __init__(self, app, ev_cls):
        super(TimerEventSender, self).__init__(self._timeout)
        self._app = app
        self._ev_cls = ev_cls

    def _timeout(self):
        self._app.send_event(self._app.name, self._ev_cls())

class EventletIOFactory(object):

    @staticmethod
    def create_custom_event():
        LOG.debug('Create CustomEvent called')
        return hub.Event()

    @staticmethod
    def create_looping_call(funct, *args, **kwargs):
        LOG.debug('create_looping_call called')
        return LoopingCall(funct, *args, **kwargs)


# TODO: improve Timer service and move it into framework
class LoopingCall(object):
    """Call a function repeatedly.
    """
    def __init__(self, funct, *args, **kwargs):
        self._funct = funct
        self._args = args
        self._kwargs = kwargs
        self._running = False
        self._interval = 0
        self._self_thread = None

    @property
    def running(self):
        return self._running

    @property
    def interval(self):
        return self._interval

    def __call__(self):
        if self._running:
            # Schedule next iteration of the call.
            self._self_thread = hub.spawn_after(self._interval, self)
        self._funct(*self._args, **self._kwargs)

    def start(self, interval, now=True):
        """Start running pre-set function every interval seconds.
        """
        if interval < 0:
            raise ValueError('interval must be >= 0')

        if self._running:
            self.stop()

        self._running = True
        self._interval = interval
        if now:
            self._self_thread = hub.spawn_after(0, self)
        else:
            self._self_thread = hub.spawn_after(self._interval, self)

    def stop(self):
        """Stop running scheduled function.
        """
        self._running = False
        if self._self_thread is not None:
            self._self_thread.cancel()
            self._self_thread = None

    def reset(self):
        """Skip the next iteration and reset timer.
        """
        if self._self_thread is not None:
            # Cancel currently scheduled call
            self._self_thread.cancel()
            self._self_thread = None
        # Schedule a new call
        self._self_thread = hub.spawn_after(self._interval, self)
