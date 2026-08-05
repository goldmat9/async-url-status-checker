#!/usr/bin/env python3
"""Async bulk URL status checker.

Reads URLs from a CSV file (one per line, or a `url` column) or an XML
sitemap, checks them concurrently with aiohttp, and reports status codes,
response times, redirect chains, and broken links.

Usage:
    python url_checker.py urls.csv
    python url_checker.py https://example.com/sitemap.xml -o report.csv
    python url_checker.py urls.csv --concurrency 50 --timeout 15
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import aiohttp

USER_AGENT = "async-url-status-checker/1.0 (+https://github.com/)"
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


@dataclass
class CheckResult:
    url: str
    status: int | None
    elapsed_ms: int
    final_url: str
    redirect_chain: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.status is not None and 200 <= self.status < 400

    @property
    def redirected(self) -> bool:
        return len(self.redirect_chain) > 0


def load_urls(source: str) -> list[str]:
    """Load URLs from a CSV file, a plain-text list, or an XML sitemap (path or URL)."""
    if source.startswith(("http://", "https://")) and source.endswith(".xml"):
        return asyncio.run(_fetch_sitemap(source))

    path = Path(source)
    text = path.read_text(encoding="utf-8")

    if path.suffix == ".xml" or text.lstrip().startswith("<?xml"):
        return parse_sitemap(text)

    urls: list[str] = []
    reader = csv.reader(text.splitlines())
    for i, row in enumerate(reader):
        if not row:
            continue
        cell = row[0].strip()
        if i == 0 and cell.lower() == "url":  # header row
            continue
        if cell.startswith(("http://", "https://")):
            urls.append(cell)
    return urls


def parse_sitemap(xml_text: str) -> list[str]:
    """Extract <loc> URLs from sitemap XML text."""
    root = ET.fromstring(xml_text)
    locs = root.findall(f".//{SITEMAP_NS}loc") or root.findall(".//loc")
    return [loc.text.strip() for loc in locs if loc.text]


async def _fetch_sitemap(url: str) -> list[str]:
    async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            return parse_sitemap(await resp.text())


async def check_url(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    url: str,
    timeout: float,
) -> CheckResult:
    """Check a single URL, following redirects and recording the chain."""
    async with semaphore:
        start = time.perf_counter()
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout), allow_redirects=True
            ) as resp:
                elapsed = int((time.perf_counter() - start) * 1000)
                chain = [str(r.url) for r in resp.history]
                return CheckResult(
                    url=url,
                    status=resp.status,
                    elapsed_ms=elapsed,
                    final_url=str(resp.url),
                    redirect_chain=chain,
                )
        except Exception as exc:  # noqa: BLE001 - report any failure as data
            elapsed = int((time.perf_counter() - start) * 1000)
            return CheckResult(
                url=url,
                status=None,
                elapsed_ms=elapsed,
                final_url="",
                error=f"{type(exc).__name__}: {exc}",
            )


async def run_checks(
    urls: list[str], concurrency: int = 20, timeout: float = 20.0
) -> list[CheckResult]:
    semaphore = asyncio.Semaphore(concurrency)
    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(
        connector=connector, headers={"User-Agent": USER_AGENT}
    ) as session:
        tasks = [check_url(session, semaphore, u, timeout) for u in urls]
        return await asyncio.gather(*tasks)


def write_report(results: list[CheckResult], output: str) -> None:
    with open(output, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["url", "status", "elapsed_ms", "redirects", "final_url", "error"]
        )
        for r in results:
            writer.writerow(
                [
                    r.url,
                    r.status if r.status is not None else "",
                    r.elapsed_ms,
                    " -> ".join(r.redirect_chain),
                    r.final_url,
                    r.error or "",
                ]
            )


def print_summary(results: list[CheckResult]) -> None:
    total = len(results)
    broken = [r for r in results if not r.ok]
    redirected = [r for r in results if r.redirected]
    times = sorted(r.elapsed_ms for r in results if r.error is None)

    print(f"\nChecked {total} URLs")
    print(f"  OK (2xx/3xx):      {total - len(broken)}")
    print(f"  Broken/errored:    {len(broken)}")
    print(f"  With redirects:    {len(redirected)}")
    if times:
        mid = len(times) // 2
        median = times[mid] if len(times) % 2 else (times[mid - 1] + times[mid]) // 2
        print(f"  Response time:     median {median} ms, max {times[-1]} ms")

    if broken:
        print("\nBroken / errored URLs:")
        for r in broken[:20]:
            detail = r.error or f"HTTP {r.status}"
            print(f"  [{detail}] {r.url}")
        if len(broken) > 20:
            print(f"  ... and {len(broken) - 20} more (see report)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Async bulk URL status checker — concurrent checks, "
        "redirect-chain mapping, broken-link reports."
    )
    parser.add_argument("source", help="CSV/TXT file of URLs, or XML sitemap (path or URL)")
    parser.add_argument("-o", "--output", default="url_report.csv", help="CSV report path")
    parser.add_argument("-c", "--concurrency", type=int, default=20, help="max concurrent requests")
    parser.add_argument("-t", "--timeout", type=float, default=20.0, help="per-request timeout (s)")
    args = parser.parse_args(argv)

    urls = load_urls(args.source)
    if not urls:
        print("No URLs found in the provided source.", file=sys.stderr)
        return 1

    print(f"Checking {len(urls)} URLs (concurrency={args.concurrency})...")
    results = asyncio.run(run_checks(urls, args.concurrency, args.timeout))

    print_summary(results)
    write_report(results, args.output)
    print(f"\nFull report written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
