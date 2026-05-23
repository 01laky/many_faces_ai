"""AI-RA17…RA20 — public stats HTTP fetch helper."""

from unittest.mock import MagicMock, patch

from services.public_stats_fetcher import fetch_public_stats


def test_ai_ra17_rejects_non_http_scheme():
    body, error = fetch_public_stats("ftp://example.com/stats")
    assert body == ""
    assert "http" in error.lower()


def test_ai_ra18_rejects_empty_url():
    body, error = fetch_public_stats("   ")
    assert body == ""
    assert error


@patch("utils.http_json.urllib.request.urlopen")
def test_ai_ra19_returns_body_on_success(mock_urlopen):
    response = MagicMock()
    response.read.return_value = b'{"usersCount":3}'
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    mock_urlopen.return_value = response

    body, error = fetch_public_stats("http://127.0.0.1:8080/api/stats/public")
    assert error == ""
    assert body == '{"usersCount":3}'


@patch("utils.http_json.urllib.request.urlopen")
def test_ai_ra20_maps_http_error(mock_urlopen):
    import urllib.error

    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="http://127.0.0.1/stats",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None,
    )
    body, error = fetch_public_stats("http://127.0.0.1/stats")
    assert body == ""
    assert "HTTP 404" in error
