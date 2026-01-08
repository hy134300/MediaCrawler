import time
import asyncio

class RateLimiter:
    """
    简单带宽限速器（bytes / second）
    """
    def __init__(self, rate_bytes_per_sec: int):
        self.rate = rate_bytes_per_sec
        self._last_check = time.monotonic()
        self._allowance = rate_bytes_per_sec

    async def wait(self, chunk_size: int):
        now = time.monotonic()
        elapsed = now - self._last_check
        self._last_check = now

        self._allowance += elapsed * self.rate
        if self._allowance > self.rate:
            self._allowance = self.rate

        if self._allowance < chunk_size:
            sleep_time = (chunk_size - self._allowance) / self.rate
            await asyncio.sleep(sleep_time)
            self._allowance = 0
        else:
            self._allowance -= chunk_size
