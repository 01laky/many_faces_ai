"""
SHV2 PI-4: normalize untrusted title/body/media URL before ReviewContent classification.

Mirrors many_faces_backend ``ContentModerationInputSanitizer`` (defense in depth).
"""

from __future__ import annotations

MAX_TITLE_LENGTH = 200
MAX_BODY_LENGTH_FOR_AI = 100_000
MAX_MEDIA_URL_LENGTH = 2000

_STRIP_ORDS = frozenset(
    {
        0x061C,
        0x200B,
        0x200C,
        0x200D,
        0x200E,
        0x200F,
        0x202A,
        0x202B,
        0x202C,
        0x202D,
        0x202E,
        0x2066,
        0x2067,
        0x2068,
        0x2069,
        0xFEFF,
    }
)


def _trim_and_strip_controls(value: str | None, max_length: int) -> str:
    if not value:
        return ""
    out: list[str] = []
    length = 0
    for ch in value:
        if length >= max_length:
            break
        o = ord(ch)
        if o in _STRIP_ORDS:
            continue
        if 0 <= o < 32 and ch not in "\n\r\t":
            continue
        out.append(ch)
        length += 1
    return "".join(out).strip()


def sanitize_for_review(
    title: str | None, body: str | None, media_url: str | None
) -> tuple[str, str, str | None]:
    t = _trim_and_strip_controls((title or "").strip(), MAX_TITLE_LENGTH)
    b = _trim_and_strip_controls((body or "").strip(), MAX_BODY_LENGTH_FOR_AI)
    m_raw = (media_url or "").strip()
    if not m_raw:
        return t, b, None
    m = _trim_and_strip_controls(m_raw, MAX_MEDIA_URL_LENGTH)
    return t, b, (m or None)
