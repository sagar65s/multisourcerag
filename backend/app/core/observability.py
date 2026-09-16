import logging
import sys
from collections import defaultdict
from datetime import UTC, datetime
from threading import Lock
from time import monotonic

import structlog


def configure_logging(level: str) -> None:
    logging.basicConfig(stream=sys.stdout, level=getattr(logging, level.upper(), logging.INFO), format="%(message)s", force=True)
    # Provider clients may include credentials or private query details in
    # request URLs. Application telemetry records only safe provider metadata.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


class OperationalMetrics:
    """Process-local, bounded-cardinality request metrics containing no user content."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = datetime.now(UTC)
        self._started_monotonic = monotonic()
        self._active = 0
        self._total = 0
        self._server_errors = 0
        self._duration_ms = 0
        self._routes: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"requests": 0, "errors": 0, "duration_ms": 0})

    def begin(self) -> None:
        with self._lock:
            self._active += 1

    def finish(self, method: str, route: str, status_code: int, duration_ms: int) -> None:
        safe_method = method if method in {"GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS", "HEAD"} else "OTHER"
        safe_route = route if route.startswith("/") and len(route) <= 160 else "unmatched"
        with self._lock:
            self._active = max(0, self._active - 1)
            self._total += 1
            self._duration_ms += max(duration_ms, 0)
            if status_code >= 500:
                self._server_errors += 1
            item = self._routes[(safe_method, safe_route)]
            item["requests"] += 1
            item["duration_ms"] += max(duration_ms, 0)
            if status_code >= 400:
                item["errors"] += 1

    def snapshot(self) -> dict:
        with self._lock:
            routes = [
                {
                    "method": method,
                    "route": route,
                    "requests": value["requests"],
                    "errors": value["errors"],
                    "average_duration_ms": round(value["duration_ms"] / value["requests"]),
                }
                for (method, route), value in self._routes.items()
            ]
            routes.sort(key=lambda item: (-item["requests"], item["route"], item["method"]))
            return {
                "started_at": self._started_at,
                "uptime_seconds": round(monotonic() - self._started_monotonic),
                "active_requests": self._active,
                "total_requests": self._total,
                "server_errors": self._server_errors,
                "average_duration_ms": round(self._duration_ms / self._total) if self._total else 0,
                "routes": routes[:20],
            }


operations = OperationalMetrics()
logger = structlog.get_logger("multisource_ai")
