from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import random, time
from typing import Callable, TypeVar
from bist_terminal.models import PriceObservation

T=TypeVar("T")

@dataclass
class ProviderHealth:
    provider_id: str
    status: str = "ACTIVE"
    failures: int = 0
    last_success: str | None = None
    last_failure: str | None = None
    latency_ms: float | None = None
    latest_data_date: str | None = None
    message: str | None = None

class ProviderError(RuntimeError): pass
class RateLimited(ProviderError): pass
class Blocked(ProviderError): pass
class SchemaChanged(ProviderError): pass

class BaseProvider(ABC):
    provider_id: str
    upstream_vendor: str

    @abstractmethod
    def get_latest_price(self, ticker: str) -> PriceObservation: ...

    def get_history(self, ticker: str, start: str, end: str):
        raise NotImplementedError

    def with_retry(self, fn: Callable[[], T], waits=None, sleep=time.sleep, max_attempts=3, base_delay=2.0, multiplier=4.0, cap=60.0) -> T:
        '''Bounded exponential backoff + jitter for 429/rate-limit responses.

        ``waits`` remains injectable for deterministic tests. Production defaults
        to 2s then 8s before the third/final attempt; the circuit breaker takes
        over if the provider still fails.
        '''
        if waits is None:
            waits=[min(cap, base_delay*(multiplier**i)) for i in range(max_attempts-1)]
        waits=list(waits)
        last=None
        for attempt in range(len(waits)+1):
            try:
                return fn()
            except RateLimited as exc:
                last=exc
                if attempt >= len(waits):
                    break
                base=float(waits[attempt])
                sleep(base + random.random()*base*0.2)
        raise last if last else ProviderError('retry failed without captured exception')
