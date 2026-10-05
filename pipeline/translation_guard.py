"""Fail-closed spend guard for the Google Cloud Translation API.

Google's own quota is a backstop with enforcement lag, so a burst can overshoot
it. This guard is the authority instead: every API request first *reserves* its
characters in a durable ledger and is refused when a hard daily or monthly
ceiling would be crossed. The ceilings sit below the Console quota and the free
tier, so the Console quota never has to be the thing that stops us.

Rules:
- Reserve before send. The ledger is written before the request leaves.
- Ambiguous outcomes stay charged (timeouts, connection errors, 5xx): Google may
  have processed and billed them. Only requests Google definitively rejected
  (HTTP 4xx) are refunded.
- Fail closed. A corrupt or unreadable ledger blocks all requests.
- If Google reports the daily quota exhausted while the ledger thinks there is
  room, the ledger was wrong: trip the day shut.
- A sliding-window pacer caps characters per minute so requests never arrive as
  one burst.

Entry points call ``install_default()`` once. Nothing is guarded until they do,
so unit tests and ad hoc imports never touch the real ledger.
"""

from __future__ import annotations

import json
import os
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX
    fcntl = None  # type: ignore[assignment]

try:
    from . import google_translate
except ImportError:  # pragma: no cover - run as script
    import google_translate

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "data" / "i18n" / "spend_guard.json"
PACIFIC_TZ = ZoneInfo("America/Los_Angeles")

# Hard ceilings equal to the Console daily quota (16,000) and the free tier
# (500,000/month). The count is exact: Python len() counts code points, which is
# what Google bills, and every ambiguous request is charged. Verify against
# Console usage after a few days (compare month_chars to billed characters).
DEFAULT_HARD_DAILY_CHARS = 16_000
DEFAULT_HARD_MONTHLY_CHARS = 500_000
DEFAULT_MAX_CHARS_PER_MINUTE = 4_000


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


class SpendGuard:
    def __init__(
        self,
        path: Path = DEFAULT_PATH,
        *,
        daily_cap: int = DEFAULT_HARD_DAILY_CHARS,
        monthly_cap: int = DEFAULT_HARD_MONTHLY_CHARS,
        max_chars_per_minute: int = DEFAULT_MAX_CHARS_PER_MINUTE,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.path = Path(path)
        self.daily_cap = daily_cap
        self.monthly_cap = monthly_cap
        self.max_chars_per_minute = max_chars_per_minute
        self._now = now
        self._monotonic = monotonic
        self._sleep = sleep
        self._window: deque[tuple[float, int]] = deque()

    # -- ledger I/O ---------------------------------------------------------

    def _periods(self) -> tuple[str, str]:
        local = self._now().astimezone(PACIFIC_TZ)  # Google's quota/billing clock
        return local.strftime("%Y-%m"), local.strftime("%Y-%m-%d")

    def _mutate(self, fn: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        """Read-modify-write the ledger under an exclusive lock."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a+", encoding="utf-8") as fh:
            if fcntl is not None:
                fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                fh.seek(0)
                raw = fh.read().strip()
                if raw:
                    try:
                        state = json.loads(raw)
                    except json.JSONDecodeError as exc:
                        raise google_translate.SpendLimitError(
                            f"spend guard ledger is corrupt: {exc}", reason="spend_guard_unreadable"
                        ) from exc
                    if not isinstance(state, dict):
                        raise google_translate.SpendLimitError(
                            "spend guard ledger is not an object", reason="spend_guard_unreadable"
                        )
                else:
                    state = {}
                month, day = self._periods()
                if state.get("month") != month:
                    state["month"], state["month_chars"] = month, 0
                if state.get("day") != day:
                    state["day"], state["day_chars"] = day, 0
                state.setdefault("month_chars", 0)
                state.setdefault("day_chars", 0)
                fn(state)
                state["updated_at"] = self._now().isoformat()
                fh.seek(0)
                fh.truncate()
                fh.write(json.dumps(state, indent=2) + "\n")
                fh.flush()
                return state
            finally:
                if fcntl is not None:
                    fcntl.flock(fh, fcntl.LOCK_UN)

    # -- public API ---------------------------------------------------------

    def reserve(self, chars: int) -> None:
        """Pace, then charge ``chars`` or raise SpendLimitError (nothing charged)."""
        if chars <= 0:
            return

        def _charge(state: dict[str, Any]) -> None:
            if state["day_chars"] + chars > self.daily_cap:
                raise google_translate.SpendLimitError(
                    f"daily spend guard: {state['day_chars']} + {chars} > {self.daily_cap}",
                    reason="spend_guard_daily",
                )
            if state["month_chars"] + chars > self.monthly_cap:
                raise google_translate.SpendLimitError(
                    f"monthly spend guard: {state['month_chars']} + {chars} > {self.monthly_cap}",
                    reason="spend_guard_monthly",
                )
            state["day_chars"] += chars
            state["month_chars"] += chars

        self._mutate(_charge)
        self._pace(chars)

    def refund(self, chars: int) -> None:
        """Undo a reservation for a request Google definitively rejected."""
        if chars <= 0:
            return

        def _undo(state: dict[str, Any]) -> None:
            state["day_chars"] = max(0, state["day_chars"] - chars)
            state["month_chars"] = max(0, state["month_chars"] - chars)

        self._mutate(_undo)

    def trip_day(self) -> None:
        """Google says today's quota is gone: stop spending until Pacific midnight."""

        def _trip(state: dict[str, Any]) -> None:
            state["day_chars"] = max(state["day_chars"], self.daily_cap)
            state["tripped_at"] = self._now().isoformat()

        self._mutate(_trip)

    # -- pacing -------------------------------------------------------------

    def _pace(self, chars: int) -> None:
        """Keep sent characters under max_chars_per_minute (a lone oversize request passes)."""
        limit = self.max_chars_per_minute
        if limit <= 0:
            return
        while True:
            now = self._monotonic()
            while self._window and now - self._window[0][0] >= 60.0:
                self._window.popleft()
            used = sum(c for _, c in self._window)
            if not self._window or used + chars <= limit:
                self._window.append((now, chars))
                return
            self._sleep(max(0.05, 60.0 - (now - self._window[0][0])))


def install_default(
    path: Path | None = None,
    *,
    now: Callable[[], datetime] | None = None,
) -> SpendGuard | None:
    """Install the guard from env config. ``GOOGLE_TRANSLATE_GUARD=0`` disables it."""
    if os.environ.get("GOOGLE_TRANSLATE_GUARD", "1") == "0":
        google_translate.set_spend_guard(None)
        return None
    kwargs: dict[str, Any] = {}
    if now is not None:
        kwargs["now"] = now
    guard = SpendGuard(
        Path(os.environ.get("GOOGLE_TRANSLATE_GUARD_PATH") or path or DEFAULT_PATH),
        daily_cap=_int_env("GOOGLE_TRANSLATE_HARD_DAILY_CHARS", DEFAULT_HARD_DAILY_CHARS),
        monthly_cap=_int_env("GOOGLE_TRANSLATE_HARD_MONTHLY_CHARS", DEFAULT_HARD_MONTHLY_CHARS),
        max_chars_per_minute=_int_env("GOOGLE_TRANSLATE_MAX_CHARS_PER_MINUTE", DEFAULT_MAX_CHARS_PER_MINUTE),
        **kwargs,
    )
    google_translate.set_spend_guard(guard)
    return guard
