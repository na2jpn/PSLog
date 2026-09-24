"""Canonical PSLog logbook locations and amateur-log discovery.

Keep log type routing here rather than teaching individual screens to glob a
folder directly.  Amateur radio logs currently live in ``logbook``; free-radio logs live in ``logbook_flr``.  The latter is intentionally not
mixed into amateur searches/awards.
"""
from pathlib import Path
import re

AMATEUR_DIRNAME = 'logbook'
FREE_RADIO_DIRNAME = 'logbook_flr'

_LOG_NAME = re.compile(r'([0-9]{4})_([A-Za-z0-9-]+)_(.*)\.txt')


def ensure_logbook_directories(root):
    """Create the two persistent amateur/free-radio log roots used by PSLog."""
    root = Path(root).resolve()
    amateur = root / AMATEUR_DIRNAME
    free_radio = root / FREE_RADIO_DIRNAME
    amateur.mkdir(parents=True, exist_ok=True)
    free_radio.mkdir(parents=True, exist_ok=True)
    return amateur, free_radio


def file_identity(path):
    """Return ``(year, station_call, suffix)`` for a PSLog amateur filename."""
    match = _LOG_NAME.fullmatch(Path(path).name)
    if not match:
        return None
    return match[1], match[2].replace('-', '/').upper(), match[3]


def base_station_call(value):
    """Strip portable/area suffixes from a station callsign."""
    return str(value or '').strip().upper().split('/', 1)[0]


def amateur_log_files(repo):
    """Return valid PSLog amateur-radio log files only.

    The path comes from ``Repository.book`` but a valid PSLog amateur filename
    is also required.  This is the common discovery entry point for new code;
    free-radio logs use their own store/API.
    """
    return sorted(
        (p for p in repo.book.glob('*.txt') if file_identity(p)),
        key=lambda p: p.name.casefold(),
    )


def amateur_station_calls(repo, preferred=''):
    """Return base amateur station calls found in valid PSLog log filenames."""
    preferred = base_station_call(preferred)
    calls = {
        base_station_call(identity[1])
        for path in amateur_log_files(repo)
        if (identity := file_identity(path)) and base_station_call(identity[1])
    }
    if preferred:
        calls.add(preferred)
    ordered = sorted(calls)
    if preferred in ordered:
        ordered.remove(preferred)
        ordered.insert(0, preferred)
    return ordered
