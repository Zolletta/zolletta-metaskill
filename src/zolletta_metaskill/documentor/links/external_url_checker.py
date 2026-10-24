"""External URL checker.

Validates external URLs with a HEAD request, falling back to GET for
servers that reject HEAD. Used by the link checker when
``documentation.check_external`` is enabled.
"""

from __future__ import annotations

import urllib.error
import urllib.request


class ExternalURLChecker:
    """Validates external URLs over HTTP."""

    @staticmethod
    def validate(url: str) -> tuple[bool, str | None]:
        """Validate an external URL with a HEAD request.

        Args:
            url: The URL to check.

        Returns:
            A ``(is_valid, error)`` pair; ``error`` is ``None`` on success.

        """
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "zolletta-documentor/1.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status < 400:
                    return True, None
                return False, f"HTTP {resp.status}"  # pragma: no cover
        except urllib.error.HTTPError as e:
            # HTTPError wraps a body that defaults to a temp file, so it leaks
            # unless closed; keep the code, then release the body.
            code = e.code
            e.close()
            # Some servers don't support HEAD
            if code == 405:
                try:
                    req = urllib.request.Request(url, method="GET")
                    req.add_header("User-Agent", "zolletta-documentor/1.0")
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        return (
                            resp.status < 400,
                            None if resp.status < 400 else f"HTTP {resp.status}",
                        )
                except Exception:
                    return False, f"HTTP {code}"
            return False, f"HTTP {code}"
        except urllib.error.URLError as e:
            return False, str(e.reason)
        except Exception as e:
            return False, str(e)
