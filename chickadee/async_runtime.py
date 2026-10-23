"""Retry only a Windows event-loop initialization failure, before any work runs."""
import asyncio
from contextlib import contextmanager
import time


@contextmanager
def event_loop_runner():
    for attempt in range(5):
        runner = asyncio.Runner()
        try:
            runner.get_loop()
            break
        except OSError as error:
            runner.close()
            if getattr(error, 'winerror', None) != 10014 or attempt == 4:
                raise
            time.sleep(.1 * 2**attempt)
    try:
        yield runner
    finally:
        runner.close()
