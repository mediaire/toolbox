import time
import heapq
from _thread import RLock

"""
A thread-safe simple class for throttling, configured to allow
X events per every Y seconds. When calling the method throttle(),
throttling will occur if needed (the method will block).
"""


class Throttler():

    SLEEP_TIME = 0.05

    def __init__(self, max_events: int, per_every_seconds=60):
        self.max_events_per_minute = max_events
        self.per_every_seconds = per_every_seconds
        self.events = []
        self.lock = RLock()

    def _time_periods_elapsed(self):
        curr_time = int(time.time())
        oldest_event = heapq.nsmallest(1, self.events)[0]
        return (curr_time - oldest_event) / self.per_every_seconds

    def current_rate(self):
        if len(self.events) == 0:
            return 0

        while self._time_periods_elapsed() >= 1:
            # keep only a rotation window of 1 time period
            heapq.heappop(self.events)
            if len(self.events) == 0:
                break

        # then the current rate is simply the number of events in the queue
        return len(self.events)

    def throttle(self):
        self.lock.acquire(blocking=True)
        try:
            rate = self.current_rate()
            while rate >= self.max_events_per_minute:
                time.sleep(self.SLEEP_TIME)
                rate = self.current_rate()
            heapq.heappush(self.events, int(time.time()))
        finally:
            self.lock.release()
