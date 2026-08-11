import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self, limit: int = 30, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, identity: str, now: float | None = None) -> bool:
        timestamp = time.monotonic() if now is None else now
        requests = self._requests[identity]
        cutoff = timestamp - self.window_seconds
        while requests and requests[0] <= cutoff:
            requests.popleft()
        if len(requests) >= self.limit:
            return False
        requests.append(timestamp)
        return True
