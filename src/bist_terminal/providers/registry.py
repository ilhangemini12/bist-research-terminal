from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable
from bist_terminal.providers.base import ProviderError, Blocked, RateLimited, SchemaChanged

@dataclass
class ProviderAttempt:
    provider_id: str
    ok: bool
    value: object | None = None
    error: str | None = None
    skipped: bool = False

@dataclass
class CircuitState:
    open: bool = False
    failures: int = 0
    reason: str | None = None

class FallbackChain:
    """Run-scoped provider chain with circuit breakers.

    403/401-like Blocked, bounded 429 RateLimited, and schema changes open the
    provider circuit immediately for the rest of the run. Generic/timeout errors
    open after ``failure_threshold`` consecutive failures.
    """
    def __init__(self, providers: Iterable, failure_threshold: int = 3):
        self.providers = list(providers)
        self.failure_threshold = max(1, int(failure_threshold))
        self.circuits = {getattr(p, 'provider_id', f'p{i}'): CircuitState() for i, p in enumerate(self.providers)}

    def _pid(self, p):
        return getattr(p, 'provider_id', 'unknown')

    def _record_failure(self, p, exc: Exception):
        pid = self._pid(p); state = self.circuits.setdefault(pid, CircuitState()); state.failures += 1
        immediate = isinstance(exc, (Blocked, RateLimited, SchemaChanged))
        if immediate or state.failures >= self.failure_threshold:
            state.open = True
            state.reason = f'{type(exc).__name__}: {exc}'

    def _record_success(self, p):
        state = self.circuits.setdefault(self._pid(p), CircuitState()); state.failures = 0

    def _call(self, p, ticker):
        pid = self._pid(p); state = self.circuits.setdefault(pid, CircuitState())
        if state.open:
            return None, ProviderAttempt(pid, False, error=f'CIRCUIT_OPEN: {state.reason}', skipped=True)
        try:
            value = p.get_latest_price(ticker); self._record_success(p)
            return value, ProviderAttempt(pid, True, value=value)
        except Exception as exc:
            self._record_failure(p, exc)
            return None, ProviderAttempt(pid, False, error=f'{type(exc).__name__}: {exc}')

    def first_success(self, ticker):
        attempts = []
        for p in self.providers:
            value, attempt = self._call(p, ticker); attempts.append(attempt)
            if attempt.ok:
                return value, attempts
        raise ProviderError('All providers failed: ' + '; '.join(a.error or '' for a in attempts))

    def collect(self, ticker, limit=None):
        out = []; attempts = []
        for p in self.providers:
            value, attempt = self._call(p, ticker); attempts.append(attempt)
            if attempt.ok:
                out.append(value)
            if limit and len(out) >= limit:
                break
        return out, attempts
