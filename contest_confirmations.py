"""Policy for confirmation checkboxes shown by contest submission dialogs.

PSLog asks for confirmations only when they materially affect a submitted
category/operation.  Network/software-use restrictions are deliberately not
turned into PSLog checkboxes: their interpretation belongs to the operator and
organizer, not to the logging program.
"""
from __future__ import annotations

_HIDDEN_PHRASES=(
    'インターネット','ネット等','ネット中継','インターネット経由',
    'クラスタ','セルフスポット','スポット作業','スポットと依頼','スポット等',
    'QSO発見援助','外部手段による交信確認','事後DB','DBで補','データベース',
    'リバースエンジニアリング','ソフトウェア','ログソフト','ソフトの確認欄',
)
_OBVIOUS_PREFIXES=(
    '国内の規約対象局として、',
    '大会原典の運用制限と提出数を確認し、',
)


def show_confirmation(text):
    text=str(text or '').strip()
    if not text:return False
    if text.startswith(_OBVIOUS_PREFIXES):return False
    return not any(token in text for token in _HIDDEN_PHRASES)


def filtered_flags(flags):
    """De-duplicate confirmation strings and apply the UI/validation policy."""
    return [x for x in dict.fromkeys(flags or []) if show_confirmation(x)]


def active_flags(event,category=None,extra=()):
    values=list(event.get('required_flags',[]))
    if category:values.extend(category.get('required_flags',[]))
    values.extend(extra or ())
    return filtered_flags(values)
