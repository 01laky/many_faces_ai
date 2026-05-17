import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.ai_model_service import _sanitize_assistant_reply

_THINK_OPEN = "<" + "think" + ">"
_THINK_CLOSE = "</" + "think" + ">"


def test_strips_think_blocks():
    raw = (
        f"{_THINK_OPEN}User said ahoj in Slovak. I will answer in Slovak.{_THINK_CLOSE}\n"
        "Ahoj! Mám sa dobre, ďakujem."
    )
    assert _sanitize_assistant_reply(raw) == "Ahoj! Mám sa dobre, ďakujem."


def test_strips_mfai_prefix():
    assert _sanitize_assistant_reply("MFAI Assistant: Ahoj!") == "Ahoj!"


def test_empty_after_strip_returns_ellipsis():
    assert _sanitize_assistant_reply(f"{_THINK_OPEN}only reasoning{_THINK_CLOSE}") == "..."
