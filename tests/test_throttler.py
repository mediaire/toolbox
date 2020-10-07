import time
import unittest
from threading import Thread
from mediaire_toolbox.throttler import Throttler


class TestThrottler(unittest.TestCase):

    def test_throttler(self):
        throttler = Throttler(max_events=2,
                              per_every_seconds=1)

        start = int(time.time())
        for _ in range(0, 8):
            throttler.throttle()
        end = int(time.time())
        elapsed_seconds = end - start

        self.assertTrue(3 <= elapsed_seconds <= 4)

    def test_thread_safe(self):
        throttler = Throttler(max_events=2,
                              per_every_seconds=1)

        def test_throttler():
            for _ in range(0, 2):
                throttler.throttle()

        start = int(time.time())
        threads = []
        for _ in range(0, 8):
            thread = Thread(target=test_throttler)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        end = int(time.time())
        elapsed_seconds = int(end - start)

        self.assertTrue(7 <= elapsed_seconds <= 8)
