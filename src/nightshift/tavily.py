"""Bounded Tavily Search/Extract with receipts, a separate credit ledger and air gap.

API contract: https://docs.tavily.com/documentation/api-reference/endpoint/search
and /extract. Rates: https://docs.tavily.com/documentation/api-credits
Only explicit basic/advanced depths are supported; auto-parameters are disabled.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import math
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit

import httpx

from nightshift.llm.cache import ResponseCache, cache_key


class CreditLimitExceeded(RuntimeError):
    pass


class AirgapViolation(RuntimeError):
    pass


def content_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def public_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("retrieval requires a public HTTPS URL without credentials")
    if parsed.hostname in {"localhost", "localhost.localdomain"} or parsed.hostname.endswith(".local"):
        raise ValueError("local URLs are not allowed")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("private/reserved IP URLs are not allowed")
    return url


@dataclass
class CreditLedger:
    limit: float = 1000
    entries: list[dict] = field(default_factory=list)
    blocked: bool = False

    def __post_init__(self):
        if not math.isfinite(self.limit) or not 0 <= self.limit <= 1000:
            raise ValueError("Tavily credit cap must be between 0 and 1000")

    @property
    def used(self) -> float:
        return sum(e["credits"] for e in self.entries)

    def reserve(self, bound: float, endpoint: str) -> dict:
        if self.blocked or self.used + bound > self.limit:
            raise CreditLimitExceeded("Tavily credit cap would be exceeded")
        entry = {"endpoint": endpoint, "credits": bound, "bound": bound, "status": "pending"}
        self.entries.append(entry)
        return entry

    def settle(self, entry: dict, usage: object):
        if usage is None:
            entry["status"] = "estimated"
            return
        if type(usage) not in (int, float) or not math.isfinite(usage) or usage < 0:
            raise ValueError("malformed Tavily credit usage")
        entry.update(credits=float(usage), status="reported")
        if usage > entry["bound"]:
            self.blocked = True
            raise CreditLimitExceeded("Tavily reported usage above its reserved bound; reconciliation required")

    def summary(self) -> dict:
        return {"limit": self.limit, "used": self.used, "blocked": self.blocked,
                "reported": sum(e["credits"] for e in self.entries if e["status"] == "reported"),
                "estimated": sum(e["credits"] for e in self.entries if e["status"] == "estimated"),
                "pending": sum(e["credits"] for e in self.entries if e["status"] == "pending"),
                "entries": [dict(e) for e in self.entries]}


@dataclass(frozen=True)
class RetrievalReceipt:
    url: str
    retrieved_at: str
    content_hash: str
    excerpt: str
    request_id: str | None
    status: Literal["live", "cache"]
    endpoint: Literal["search", "extract"]
    text: str
    response_hash: str
    query: str = ""
    credits: float = 0
    credit_status: str = "reported"
    source_version: str | None = None
    version_match: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalResult:
    receipts: tuple[RetrievalReceipt, ...]
    failures: tuple[dict, ...] = ()


class TavilyClient:
    def __init__(self, api_key: str = "", *, ledger: CreditLedger | None = None,
                 airgapped: bool = False, http: httpx.AsyncClient | None = None,
                 cache: ResponseCache | None = None, namespace: str = "live"):
        self.api_key, self.airgapped = api_key, airgapped
        self.ledger = ledger if ledger is not None else CreditLedger()
        self.http = http if http is not None else httpx.AsyncClient(timeout=30, follow_redirects=False)
        self._owns_http = http is None
        self.cache = cache if cache is not None else ResponseCache(":memory:")
        self._owns_cache = cache is None
        self.namespace = namespace
        self.receipts: list[RetrievalReceipt] = []
        self.failures: list[dict] = []

    async def _request(self, endpoint: str, body: dict, bound: float) -> RetrievalResult:
        # Check before the cache too: cached issue/fix text can contaminate a benchmark.
        if self.airgapped:
            raise AirgapViolation("external retrieval and its cache are disabled for benchmark runs")
        key = cache_key({"namespace": self.namespace, "endpoint": endpoint, "body": body})
        cached = self.cache.get(key)
        if cached is not None:
            result = RetrievalResult(tuple(replace(RetrievalReceipt(**r), status="cache")
                                           for r in cached["receipts"]), tuple(cached["failures"]))
            self.receipts.extend(result.receipts)
            self.failures.extend(result.failures)
            return result
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY is required for live retrieval")
        entry = self.ledger.reserve(bound, endpoint)
        try:
            response = await self.http.post(f"https://api.tavily.com/{endpoint}", json=body,
                                            headers={"Authorization": f"Bearer {self.api_key}"})
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get("results"), list):
                raise ValueError("malformed Tavily results")
            request_id = data.get("request_id") or response.headers.get("x-request-id")
            entry["request_id"] = request_id
            usage = data.get("usage") or {}
            if not isinstance(usage, dict):
                raise ValueError("malformed Tavily usage")
            self.ledger.settle(entry, usage.get("credits"))
            timestamp = datetime.now(timezone.utc).isoformat()
            digest = content_hash(json.dumps(data, sort_keys=True, ensure_ascii=False))
            receipts = []
            failures = list(data.get("failed_results") or [])
            for item in data["results"]:
                try:
                    url = public_url(str(item.get("url", "")))
                except ValueError as exc:
                    failures.append({"url": item.get("url"), "error": str(exc)})
                    continue
                if endpoint == "extract" and url not in body["urls"]:
                    failures.append({"url": url, "error": "extraction URL was not in the approved request"})
                    continue
                text = item.get("raw_content") if endpoint == "extract" else item.get("content")
                if not isinstance(text, str) or not text.strip():
                    failures.append({"url": url, "error": "empty extraction/search content"})
                    continue
                receipts.append(RetrievalReceipt(url, timestamp, content_hash(text), text[:1000], request_id,
                                                  "live", endpoint, text, digest, body.get("query", ""),
                                                  entry["credits"], entry["status"]))
            result = RetrievalResult(tuple(receipts), tuple(failures))
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {400, 401, 403, 422, 429, 432, 433}:
                entry.update(credits=0, status="rejected")
            raise
        # Transport failures/malformed 200 responses retain explicit pending exposure.
        self.receipts.extend(result.receipts)
        self.failures.extend(result.failures)
        self.cache.put(key, {"receipts": [r.to_dict() for r in result.receipts], "failures": list(result.failures)})
        return result

    async def search(self, query: str, *, domains: tuple[str, ...] = (), max_results: int = 3,
                     depth: Literal["basic", "advanced"] = "basic") -> RetrievalResult:
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 500:
            raise ValueError("search query must contain 1–500 characters")
        if depth not in {"basic", "advanced"} or type(max_results) is not int or not 1 <= max_results <= 5:
            raise ValueError("unsupported search depth/result limit")
        if len(domains) > 5 or any(not isinstance(d, str) or "/" in d for d in domains):
            raise ValueError("invalid bounded domain allowlist")
        return await self._request("search", {"query": query, "search_depth": depth,
                                  "max_results": max_results, "include_domains": list(domains),
                                  "auto_parameters": False, "include_answer": False, "include_usage": True},
                                   1 if depth == "basic" else 2)

    async def extract(self, urls: list[str] | tuple[str, ...], *,
                      depth: Literal["basic", "advanced"] = "basic") -> RetrievalResult:
        if not 1 <= len(urls) <= 20 or depth not in {"basic", "advanced"}:
            raise ValueError("extract requires 1–20 URLs and an approved depth")
        urls = list(dict.fromkeys(public_url(u) for u in urls))
        # Reserve whole batches, even if the service reports a smaller fractional cost.
        bound = math.ceil(len(urls) / 5) * (1 if depth == "basic" else 2)
        return await self._request("extract", {"urls": urls, "extract_depth": depth,
                                   "format": "text", "include_usage": True}, bound)

    async def aclose(self):
        if self._owns_http:
            await self.http.aclose()
        if self._owns_cache:
            self.cache.close()
