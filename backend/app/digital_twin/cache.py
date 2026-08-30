from __future__ import annotations

from collections import OrderedDict
from hashlib import sha256
import json
from threading import RLock
from typing import Callable, Generic, TypeVar


T = TypeVar("T")


def deterministic_key(*parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(payload).hexdigest()


class PredictionCache(Generic[T]):
    def __init__(self, max_size: int = 8_192) -> None:
        self.max_size = max(16, int(max_size))
        self._values: OrderedDict[str, T] = OrderedDict()
        self._lock = RLock()
        self.hits = 0
        self.misses = 0

    def get_or_compute(self, key: str, compute: Callable[[], T]) -> T:
        with self._lock:
            if key in self._values:
                self.hits += 1
                self._values.move_to_end(key)
                return self._values[key]
        value = compute()
        with self._lock:
            self.misses += 1
            self._values[key] = value
            self._values.move_to_end(key)
            while len(self._values) > self.max_size:
                self._values.popitem(last=False)
        return value

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {
            "size": len(self._values),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total else 0.0,
        }

