"""Looks up the US dollar → Indian rupee exchange rate (₹ for $1) from free public services."""
from __future__ import annotations

import json
import ssl
import urllib.request
from datetime import date

import certifi

# Python on Mac often lacks web certificates; use the bundled set instead.
_SSL = ssl.create_default_context(cafile=certifi.where())


def _get(url: str) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "saree-books"})
        with urllib.request.urlopen(req, timeout=6, context=_SSL) as r:
            return json.load(r)
    except Exception:
        return None


def usd_to_inr(on: date) -> tuple[float, str] | None:
    """Return (rate, source note) for the given date, or None when offline."""
    when = "latest" if on >= date.today() else on.isoformat()
    j = _get(f"https://api.frankfurter.dev/v1/{when}?base=USD&symbols=INR")
    if j and "INR" in j.get("rates", {}):
        return float(j["rates"]["INR"]), f"European Central Bank rate for {j['date']}"
    j = _get("https://open.er-api.com/v6/latest/USD")
    if j and "INR" in j.get("rates", {}):
        return float(j["rates"]["INR"]), "today's market rate"
    return None
