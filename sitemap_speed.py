#!/usr/bin/env python3
"""
sitemap_speed.py - Measure how long every page in a sitemap takes to load.

Usage examples:
    python3 sitemap_speed.py https://example.com/sitemap.xml
    python3 sitemap_speed.py https://example.com/sitemap.xml --runs 2
    python3 sitemap_speed.py https://example.com/sitemap.xml --csv results.csv --workers 4

Only uses the Python standard library (Python 3.8+).
"""

import argparse
import csv
import gzip
import statistics
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36 sitemap-speed/1.0"
)

USE_COLOR = sys.stdout.isatty()


def color(text, code):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def fetch(url, ua, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    if url.endswith(".gz") or data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return data


def collect_urls(sitemap_url, ua, timeout, seen=None):
    """Return all page URLs, following sitemap indexes recursively."""
    seen = seen if seen is not None else set()
    if sitemap_url in seen:
        return []
    seen.add(sitemap_url)

    try:
        root = ET.fromstring(fetch(sitemap_url, ua, timeout))
    except Exception as e:
        print(color(f"  ! Could not read sitemap {sitemap_url}: {e}", "33"), file=sys.stderr)
        return []

    tag = root.tag.replace(NS, "")
    locs = [el.text.strip() for el in root.iter(f"{NS}loc") if el.text]

    if tag == "sitemapindex":
        print(f"  Sitemap index with {len(locs)} sub-sitemaps: {sitemap_url}", file=sys.stderr)
        urls = []
        for sub in locs:
            urls.extend(collect_urls(sub, ua, timeout, seen))
        return urls

    print(f"  {len(locs):>4} URLs in {sitemap_url}", file=sys.stderr)
    return locs


def detect_cache(headers, body_tail):
    """Best-effort guess at whether the page came from a cache."""
    for h in ("cf-cache-status", "x-cache", "x-litespeed-cache", "x-proxy-cache"):
        if headers.get(h):
            return f"{h}: {headers.get(h)}"
    tail = body_tail.decode("utf-8", "ignore")
    if "W3 Total Cache" in tail:
        if "Page Caching using" in tail and "(User is logged in)" not in tail:
            return "W3TC: cached"
        return "W3TC: not cached"
    return "-"


def time_page(url, ua, timeout):
    """Return timing info for a single page load."""
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "identity"})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ttfb = time.perf_counter() - start
            body = resp.read()
            total = time.perf_counter() - start
            return {
                "url": url, "status": resp.status, "ttfb": ttfb, "total": total,
                "size_kb": len(body) / 1024,
                "cache": detect_cache(resp.headers, body[-2000:]),
                "error": "",
            }
    except urllib.error.HTTPError as e:
        return {"url": url, "status": e.code, "ttfb": None, "total": time.perf_counter() - start,
                "size_kb": 0, "cache": "-", "error": str(e.reason)}
    except Exception as e:
        return {"url": url, "status": 0, "ttfb": None, "total": None,
                "size_kb": 0, "cache": "-", "error": str(e)}


def speed_color(seconds, slow):
    if seconds is None:
        return color("   error", "31")
    text = f"{seconds:7.2f}s"
    if seconds >= slow:
        return color(text, "31")          # red
    if seconds >= slow / 2:
        return color(text, "33")          # yellow
    return color(text, "32")              # green


def main():
    p = argparse.ArgumentParser(description="Time how long each page in a sitemap takes to load.")
    p.add_argument("sitemap", help="Sitemap or sitemap index URL")
    p.add_argument("--runs", type=int, default=1,
                   help="Load each page this many times (2 shows cold vs. cached). Default 1")
    p.add_argument("--workers", type=int, default=1,
                   help="Pages to load in parallel. Keep low on small servers. Default 1")
    p.add_argument("--timeout", type=float, default=30, help="Seconds before giving up on a page. Default 30")
    p.add_argument("--slow", type=float, default=2.0, help="Seconds counted as slow (shown red). Default 2")
    p.add_argument("--limit", type=int, default=0, help="Only test the first N URLs")
    p.add_argument("--csv", metavar="FILE", help="Also save results to a CSV file")
    p.add_argument("--user-agent", default=DEFAULT_UA, help="User-Agent header to send")
    args = p.parse_args()

    print("Reading sitemap...", file=sys.stderr)
    urls = list(dict.fromkeys(collect_urls(args.sitemap, args.user_agent, args.timeout)))
    if args.limit:
        urls = urls[: args.limit]
    if not urls:
        sys.exit("No URLs found.")

    print(f"\nTesting {len(urls)} pages, {args.runs} run(s) each\n")
    header = f"{'RUN':>3}  {'STATUS':>6}  {'TTFB':>8}  {'TOTAL':>8}  {'SIZE':>8}  {'CACHE':<18}  URL"
    print(header)
    print("-" * len(header))

    results = []
    for run in range(1, args.runs + 1):
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            for r in pool.map(lambda u: time_page(u, args.user_agent, args.timeout), urls):
                r["run"] = run
                results.append(r)
                status = color(str(r["status"] or "ERR"), "32" if r["status"] == 200 else "31")
                ttfb = f"{r['ttfb']:7.2f}s" if r["ttfb"] is not None else "       -"
                extra = f"  ({r['error']})" if r["error"] else ""
                print(f"{run:>3}  {status:>6}  {ttfb}  {speed_color(r['total'], args.slow)}  "
                      f"{r['size_kb']:6.0f}KB  {r['cache']:<18}  {r['url']}{extra}")

    # Summary per run
    print()
    for run in range(1, args.runs + 1):
        ok = [r for r in results if r["run"] == run and r["status"] == 200 and r["total"] is not None]
        failed = sum(1 for r in results if r["run"] == run) - len(ok)
        if not ok:
            print(f"Run {run}: no successful loads ({failed} failed)")
            continue
        times = [r["total"] for r in ok]
        slow = sum(t >= args.slow for t in times)
        print(f"Run {run}: {len(ok)} OK, {failed} failed | "
              f"avg {statistics.mean(times):.2f}s, median {statistics.median(times):.2f}s, "
              f"fastest {min(times):.2f}s, slowest {max(times):.2f}s | {slow} slower than {args.slow}s")

    last_ok = sorted((r for r in results
                      if r["run"] == args.runs and r["status"] == 200 and r["total"] is not None),
                     key=lambda r: r["total"], reverse=True)[:5]
    if last_ok:
        print("\nSlowest pages:")
        for r in last_ok:
            print(f"  {r['total']:6.2f}s  {r['url']}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["run", "url", "status", "ttfb", "total", "size_kb", "cache", "error"])
            w.writeheader()
            for r in results:
                w.writerow({**r,
                            "ttfb": round(r["ttfb"], 3) if r["ttfb"] is not None else "",
                            "total": round(r["total"], 3) if r["total"] is not None else "",
                            "size_kb": round(r["size_kb"], 1)})
        print(f"\nSaved results to {args.csv}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nStopped.")
