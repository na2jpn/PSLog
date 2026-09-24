"""Pure helpers for record-time drift checks (no Qt dependency)."""
from __future__ import annotations

from datetime import datetime


def drift_seconds(date_text: str, time_text: str, now: datetime) -> float:
    """Return absolute difference between entered JST-like local time and ``now``.

    The QSO model has already normalized the strings to YYYY-MM-DD / HH:MM.
    ``now`` supplies the timezone so this helper stays independent of global
    timezone state while remaining easy to test.
    """
    entered=datetime.strptime(f'{date_text} {time_text}','%Y-%m-%d %H:%M')
    if now.tzinfo is not None:
        entered=entered.replace(tzinfo=now.tzinfo)
    return abs((now-entered).total_seconds())


def needs_confirmation(date_text: str, time_text: str, now: datetime, threshold_minutes: int=3) -> bool:
    return drift_seconds(date_text,time_text,now) >= int(threshold_minutes)*60
