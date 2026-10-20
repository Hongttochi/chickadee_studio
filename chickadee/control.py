"""Cooperative scan control: finish the current page before pausing."""
import asyncio
from threading import Event, Lock
import time


class ScanControl:
    def __init__(self):
        self.requested = Event()
        self.paused = Event()
        self._lock = Lock()
        self._since = None
        self._total = 0.0

    def pause(self):
        self.requested.set()

    def resume(self):
        self.requested.clear()

    @property
    def paused_seconds(self):
        with self._lock:
            return self._total + (time.monotonic() - self._since if self._since is not None else 0)

    async def checkpoint(self, emit):
        if not self.requested.is_set():
            return
        with self._lock:
            self._since = time.monotonic()
        self.paused.set()
        emit({'kind': 'control', 'state': 'paused', 'message': '일시정지 · 다음 페이지 검사를 기다립니다.'})
        try:
            while self.requested.is_set():
                await asyncio.sleep(.05)
        finally:
            with self._lock:
                self._total += time.monotonic() - self._since
                self._since = None
            self.paused.clear()
        emit({'kind': 'control', 'state': 'running', 'message': '검사 재개 · 남은 페이지를 이어서 검사합니다.'})
