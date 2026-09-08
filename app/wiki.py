"""Live Wikipedia proxy — search real pages and pull their plain text for NER testing.

Server-side proxy avoids browser CORS, adds caching, a polite User-Agent,
and truncates extracts to the model's max input length.
"""
from __future__ import annotations

import html
import logging
import re
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

from .model import settings

log = logging.getLogger("geoner.wiki")

WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = "GeoNER-Geopolitical-Demo/1.0 (FastAPI demo; contact: admin@example.com)"
CACHE_TTL = 600  # seconds

router = APIRouter(prefix="/api/wiki", tags=["wikipedia"])

_cache: Dict[tuple, tuple] = {}


async def _wiki(params: Dict[str, Any]) -> Dict[str, Any]:
    params = {**params, "format": "json", "utf8": "1"}
    key = tuple(sorted(params.items()))
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            r = await client.get(WIKI_API, params=params, headers={"User-Agent": UA})
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as exc:
        log.warning("Wikipedia API error: %s", exc)
        raise HTTPException(502, f"Wikipedia API unreachable: {exc}")
    if len(_cache) > 500:                      # simple memory guard
        _cache.clear()
    _cache[key] = (now, data)
    return data


@router.get("/search")
async def search(
    q: str = Query(..., min_length=2, max_length=200, description="Wikipedia search query"),
    limit: int = Query(8, ge=1, le=20),
):
    """Search real Wikipedia pages (titles + snippets)."""
    data = await _wiki({"action": "query", "list": "search", "srsearch": q, "srlimit": limit})
    results: List[Dict[str, Any]] = []
    for item in data.get("query", {}).get("search", []):
        snippet = html.unescape(re.sub(r"<[^>]+>", "", item.get("snippet", "")))
        results.append({
            "pageid": item.get("pageid"),
            "title": item.get("title"),
            "snippet": snippet.strip(),
            "wordcount": item.get("wordcount"),
        })
    return {"query": q, "results": results}


@router.get("/page")
async def page(
    title: Optional[str] = Query(None, max_length=300),
    pageid: Optional[int] = Query(None),
):
    """Fetch the plain-text extract of a Wikipedia page (truncated to model max length)."""
    if not title and pageid is None:
        raise HTTPException(422, "Provide either 'title' or 'pageid'")
    params: Dict[str, Any] = {
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "redirects": "1",
    }
    if pageid is not None:
        params["pageids"] = str(pageid)
    else:
        params["titles"] = title

    data = await _wiki(params)
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        raise HTTPException(404, "Wikipedia page not found")
    p = next(iter(pages.values()))
    if "missing" in p:
        raise HTTPException(404, "Wikipedia page not found")

    extract = re.sub(r"\n{3,}", "\n\n", p.get("extract", "") or "").strip()
    if not extract:
        raise HTTPException(404, "Page has no extractable text")

    max_len = settings.max_text_len
    truncated = len(extract) > max_len
    if truncated:
        cut = extract[:max_len]
        cut = cut[: cut.rfind(" ")]            # cut on word boundary
        extract = cut + " …"

    return {
        "title": p.get("title"),
        "pageid": p.get("pageid"),
        "url": f"https://en.wikipedia.org/?curid={p.get('pageid')}",
        "text": extract,
        "chars": len(extract),
        "truncated": truncated,
        "license": "CC BY-SA 4.0 (Wikipedia contributors)",
    }
