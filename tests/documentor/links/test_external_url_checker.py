"""Tests for external_url_checker.py."""

from __future__ import annotations

import email.message
import urllib.error
from unittest.mock import MagicMock, patch

from zolletta_metaskill.documentor.links.external_url_checker import ExternalURLChecker


class TestExternalURLChecker:
    """ExternalURLChecker validates external URLs over HTTP."""

    # --- validate_external_url ---

    def test_magicmock_success_returns_none(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            valid, error = ExternalURLChecker.validate("https://example.com")
        assert valid is True
        assert error is None

    def test_http_error_405_fallback_get(self) -> None:
        import email.message
        import urllib.error

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = [
                urllib.error.HTTPError(
                    "url",
                    405,
                    "Method Not Allowed",
                    email.message.Message(),
                    None,
                ),
                mock_resp,
            ]
            valid, error = ExternalURLChecker.validate("https://example.com")
        assert valid is True

    def test_http_error_404(self) -> None:
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                "url",
                404,
                "Not Found",
                email.message.Message(),
                None,
            ),
        ):
            valid, error = ExternalURLChecker.validate("https://example.com")
        assert valid is False
        assert error is not None
        assert "404" in error

    def test_urlerror_url_error_contains_connection_refused(self) -> None:
        err = urllib.error.URLError("connection refused")
        err.reason = "connection refused"
        with patch("urllib.request.urlopen", side_effect=err):
            valid, error = ExternalURLChecker.validate("https://example.com")
        assert valid is False
        assert error is not None
        assert "connection refused" in error

    def test_validate_external_url_generic_exception_contains_boom(self) -> None:
        with patch("urllib.request.urlopen", side_effect=Exception("boom")):
            valid, error = ExternalURLChecker.validate("https://example.com")
        assert valid is False
        assert error is not None
        assert "boom" in error

    def test_405_get_fallback_failure(self) -> None:
        # Both HEAD and GET fallback raise 405
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                "url",
                405,
                "Method Not Allowed",
                email.message.Message(),
                None,
            ),
        ):
            valid, error = ExternalURLChecker.validate("https://example.com")
        assert valid is False

    def test_validate_issues_head_request_with_user_agent(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with (
            patch("urllib.request.Request") as mock_request_cls,
            patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen,
        ):
            req = mock_request_cls.return_value
            ExternalURLChecker.validate("https://example.com")
        mock_request_cls.assert_called_once_with("https://example.com", method="HEAD")
        req.add_header.assert_called_once_with("User-Agent", "zolletta-documentor/1.0")
        mock_urlopen.assert_called_once_with(req, timeout=10)

    def test_validate_status_400_returns_http_error(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            valid, error = ExternalURLChecker.validate("https://example.com")
        assert valid is False
        assert error == "HTTP 400"

    def test_405_fallback_issues_get_request_with_user_agent(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        http_405 = urllib.error.HTTPError(
            "url", 405, "Method Not Allowed", email.message.Message(), None
        )
        with (
            patch("urllib.request.Request") as mock_request_cls,
            patch("urllib.request.urlopen") as mock_urlopen,
        ):
            mock_urlopen.side_effect = [http_405, mock_resp]
            requests = [MagicMock(name="req_head"), MagicMock(name="req_get")]
            mock_request_cls.side_effect = requests
            valid, error = ExternalURLChecker.validate("https://example.com")
        assert valid is True
        assert error is None
        assert mock_request_cls.call_args_list[1].kwargs == {"method": "GET"}
        requests[1].add_header.assert_called_once_with("User-Agent", "zolletta-documentor/1.0")
        assert mock_urlopen.call_args_list[1].args == (requests[1],)
        assert mock_urlopen.call_args_list[1].kwargs == {"timeout": 10}

    def test_405_fallback_status_400_returns_http_error(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        http_405 = urllib.error.HTTPError(
            "url", 405, "Method Not Allowed", email.message.Message(), None
        )
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = [http_405, mock_resp]
            valid, error = ExternalURLChecker.validate("https://example.com")
        assert valid is False
        assert error == "HTTP 400"
