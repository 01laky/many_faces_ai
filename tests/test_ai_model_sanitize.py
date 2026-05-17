import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.ai_model_service import _sanitize_assistant_reply

_THINK_OPEN = "<" + "think" + ">"
_THINK_CLOSE = "</" + "think" + ">"


def test_strips_think_blocks():
    raw = f"{_THINK_OPEN}User said ahoj in Slovak.{_THINK_CLOSE}\nAhoj!"
    assert _sanitize_assistant_reply(raw, "ahoj") == "Ahoj!"


def test_strips_mfai_prefix():
    assert _sanitize_assistant_reply("MFAI Assistant: Ahoj!", "test") == "Ahoj!"


def test_empty_after_strip_returns_ellipsis():
    assert _sanitize_assistant_reply(f"{_THINK_OPEN}only reasoning{_THINK_CLOSE}", "x") == "..."


def test_strips_invented_json_fence():
    raw = (
        "Tu je blok:\n```json\n"
        '{"system_time": "2023-10-15T14:30:00Z", "__typename": "SystemStats"}\n'
        "```\nTeraz je 15:30 UTC."
    )
    out = _sanitize_assistant_reply(raw, "kolko je hodin")
    assert "system_time" not in out
    assert "__typename" not in out
    assert "Teraz je 15:30 UTC" in out


def test_trims_parroted_closing_unless_user_asked_wellbeing():
    assert (
        _sanitize_assistant_reply(
            "Neexistuje telefónne číslo. Mám sa dobre, ďakujem. A ty?",
            "tel mi nieco",
        )
        == "Neexistuje telefónne číslo."
    )
    assert (
        _sanitize_assistant_reply("Mám sa dobre, ďakujem. A ty?", "ako sa máš?")
        == "Mám sa dobre, ďakujem. A ty?"
    )
