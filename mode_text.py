"""PSLog MODE field helper for the optional UI Sub qualifier.

The TXT format remains one MODE string.  Known ADIF mode names that themselves
contain spaces (e.g. "VARA HF") are kept intact; an extra qualifier may follow.
"""
from adif_modes import MODES

KNOWN_SPACE_MODES = tuple(
    sorted((name for name in MODES if ' ' in name), key=len, reverse=True)
)
KNOWN_MODES = tuple(sorted(MODES, key=len, reverse=True))


def split_mode_value(value):
    value = (value or '').strip()
    if not value:
        return '', ''
    upper = value.upper()

    # An exact known mode, including names such as VARA HF, has no PSLog Sub.
    if upper in MODES:
        return value, ''

    # If a known mode is followed by extra text, treat only that extra text as
    # the PSLog Sub qualifier.  Longest match is important for VARA FM 1200.
    for known in KNOWN_MODES:
        prefix = known + ' '
        if upper.startswith(prefix):
            return value[:len(known)], value[len(known):].strip()

    # Unknown mode names are preserved verbatim rather than guessed/split.
    return value, ''


def combine_mode_value(main, sub='', sub_enabled=True):
    main = (main or '').strip()
    sub = (sub or '').strip()
    if sub_enabled and main and sub:
        return main + ' ' + sub
    return main
