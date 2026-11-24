"""Next-to-send contest numbers, stored independently in each contest tab."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re

from input_normalization import machine_text

STATE_KEYS = ('number_increment', 'number_per_band', 'number_initial',
              'number_started', 'number_by_band')


def increment(value):
    """Increment the trailing digit run, preserving its minimum width."""
    value = machine_text(value, upper=True)
    match = re.search(r'[0-9]+$', value)
    if not match:
        return value
    digits = match.group()
    return value[:match.start()] + str(int(digits) + 1).zfill(len(digits))


def band_key(value):
    value = machine_text(value)
    try:
        number = Decimal(value)
        if number.is_finite() and number > 0:
            return format(number.normalize(), 'f')
    except InvalidOperation:
        pass
    return value


def normal_state(raw):
    initial = raw.get('number_initial', '')
    numbers = raw.get('number_by_band', {})
    return {
        'number_increment': bool(raw.get('number_increment', False)),
        'number_per_band': bool(raw.get('number_per_band', False)),
        'number_initial': machine_text(initial, upper=True) if isinstance(initial, str) else '',
        'number_started': bool(raw.get('number_started', False)),
        'number_by_band': {band_key(k): machine_text(v, upper=True)
                           for k, v in numbers.items() if isinstance(k, str) and isinstance(v, str)}
                          if isinstance(numbers, dict) else {},
    }


def remember(session, band, value):
    value = machine_text(value, upper=True)
    session['own_exchange'] = value
    if session.get('number_increment'):
        # The operator may enable the option before typing the initial number.
        # Until the first saved QSO, the edited value is the common starting value.
        if not session.get('number_started') or not session.get('number_initial'):
            session['number_initial'] = value
        if session.get('number_per_band'):
            session.setdefault('number_by_band', {})[band_key(band)] = value
    return value


def configure(session, band, value, enabled, per_band):
    remember(session, band, value)
    session.update(number_increment=bool(enabled), number_per_band=bool(per_band))
    return remember(session, band, value)


def change_band(session, old_band, new_band, value):
    value = remember(session, old_band, value)
    if session.get('number_increment') and session.get('number_per_band'):
        value = session.get('number_by_band', {}).get(band_key(new_band),
                                                     session.get('number_initial') or value)
        session.setdefault('number_by_band', {})[band_key(new_band)] = value
    session['own_exchange'] = value
    return value


def recorded(session, band, sent_value):
    """Call only after the QSO has been successfully written to its log."""
    value = remember(session, band, sent_value)
    if session.get('number_increment'):
        value = increment(value)
        session['number_started'] = True
        session['own_exchange'] = value
        if session.get('number_per_band'):
            session.setdefault('number_by_band', {})[band_key(band)] = value
    return value
