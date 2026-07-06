from __future__ import annotations

import os
from typing import Iterable

from flask import Flask, Response, request


def _csp() -> str:
    # CDN-based app: allow required CDNs + inline for Babel/React UMD (dev-friendly).
    # If you later bundle assets, we can tighten this to nonces/hashes.
    return "; ".join(
        [
            "default-src 'self'",
            "base-uri 'self'",
            "object-src 'none'",
            "frame-ancestors 'none'",
            "img-src 'self' data: https:",
            "media-src 'self' https:",
            "connect-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
            "font-src 'self' https://fonts.gstatic.com",
        ]
    )


def install_security(app: Flask) -> None:
    """
    Basic production hardening:
    - Secure headers (CSP, clickjacking, sniffing, referrer)
    - Conservative permissions policy
    - Optional HSTS if behind HTTPS (set ENABLE_HSTS=1)
    """

    @app.after_request
    def _set_headers(resp: Response) -> Response:
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        resp.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        resp.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        resp.headers.setdefault("Content-Security-Policy", _csp())

        # Only enable HSTS when you are serving HTTPS (typically via reverse proxy).
        if os.getenv("ENABLE_HSTS", "0") == "1" and request.is_secure:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=15552000; includeSubDomains")

        return resp

