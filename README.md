# sitemap-speed

> Measure how long every page in a sitemap takes to load, right from your terminal.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

`sitemap_speed.py` reads a sitemap (or sitemap index), requests every page it lists, and reports status, time to first byte, total load time, page size and cache status for each one. It finishes with a summary and a list of your slowest pages.

It's a single file that uses only the Python standard library, so there's nothing to install.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Options](#options)
- [Example Output](#example-output)
- [How It Works](#how-it-works)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Follows sitemap indexes** recursively and removes duplicate URLs
- **Handles gzipped sitemaps** (`.xml.gz`)
- **Times each page**: TTFB, total load time, and response size
- **Detects caching** from Cloudflare, Varnish/`X-Cache`, LiteSpeed, Nginx proxy cache, and W3 Total Cache
- **Compares cold and warm loads** with multiple runs (`--runs 2`)
- **Loads pages in parallel** with a configurable worker count
- **Color-coded output**: green for fast, yellow for borderline, red for slow (turned off automatically when output isn't a terminal)
- **Exports to CSV** for spreadsheets or further analysis
- **Zero dependencies**, Python standard library only

## Requirements

- Python 3.8 or newer

## Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/page-speed.git
cd page-speed
```

Or download just the script:

```bash
curl -O https://raw.githubusercontent.com/<your-username>/page-speed/main/sitemap_speed.py
chmod +x sitemap_speed.py
```

## Usage

```bash
python3 sitemap_speed.py https://example.com/sitemap.xml
```

Load each page twice to compare cold and cached performance:

```bash
python3 sitemap_speed.py https://example.com/sitemap.xml --runs 2
```

Test 4 pages at a time and save the results to CSV:

```bash
python3 sitemap_speed.py https://example.com/sitemap.xml --workers 4 --csv results.csv
```

Quick check of the first 20 pages, counting anything over 1 second as slow:

```bash
python3 sitemap_speed.py https://example.com/sitemap.xml --limit 20 --slow 1
```

> [!NOTE]
> Keep `--workers` low when testing small or shared-hosting servers. Too many parallel requests can slow the site down and skew your results.

## Options

| Option | Default | Description |
| --- | --- | --- |
| `sitemap` | *(required)* | Sitemap or sitemap index URL |
| `--runs N` | `1` | Load each page `N` times. Use `2` to compare cold and cached loads |
| `--workers N` | `1` | Number of pages to load in parallel |
| `--timeout SECONDS` | `30` | Seconds to wait before giving up on a page |
| `--slow SECONDS` | `2.0` | Load time counted as slow (shown in red; yellow above half of this) |
| `--limit N` | `0` (all) | Only test the first `N` URLs |
| `--csv FILE` | — | Also save the results to a CSV file |
| `--user-agent UA` | Chrome-like UA | `User-Agent` header to send with each request |

Run `python3 sitemap_speed.py --help` to see the full list.

## Example Output

```text
Reading sitemap...
  Sitemap index with 2 sub-sitemaps: https://example.com/sitemap.xml
    12 URLs in https://example.com/page-sitemap.xml
    30 URLs in https://example.com/post-sitemap.xml

Testing 42 pages, 2 run(s) each

RUN  STATUS      TTFB     TOTAL      SIZE  CACHE               URL
-------------------------------------------------------------------
  1     200     2.41s     2.58s      84KB  cf-cache-status: MISS  https://example.com/
  1     200     0.38s     0.45s      61KB  cf-cache-status: MISS  https://example.com/about/
  ...
  2     200     0.09s     0.14s      84KB  cf-cache-status: HIT   https://example.com/

Run 1: 42 OK, 0 failed | avg 1.12s, median 0.94s, fastest 0.31s, slowest 3.20s | 6 slower than 2.0s
Run 2: 42 OK, 0 failed | avg 0.18s, median 0.15s, fastest 0.08s, slowest 0.52s | 0 slower than 2.0s

Slowest pages:
    0.52s  https://example.com/shop/
    ...
```

### CSV columns

`run`, `url`, `status`, `ttfb`, `total`, `size_kb`, `cache`, `error`

## How It Works

1. **Collect URLs.** The sitemap is downloaded (and decompressed if gzipped). If it's a sitemap index, each sub-sitemap is fetched in turn. Duplicate URLs are removed.
2. **Time each page.** Every URL is requested with `Accept-Encoding: identity`, so sizes reflect the uncompressed HTML. TTFB is measured when the response headers arrive, and total time once the full body has been read.
3. **Detect caching.** The script checks common cache headers (`cf-cache-status`, `x-cache`, `x-litespeed-cache`, `x-proxy-cache`) and the W3 Total Cache HTML footer.
4. **Summarize.** Each run gets average, median, fastest and slowest load times, and the five slowest pages from the final run are listed.

Timings cover the HTML document only. Images, scripts and stylesheets aren't loaded, so this measures server response time rather than full browser render time. For render metrics, use a tool like [Lighthouse](https://developer.chrome.com/docs/lighthouse) or [PageSpeed Insights](https://pagespeed.web.dev/).

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-change`)
3. Commit your changes (`git commit -m "Add my change"`)
4. Push the branch (`git push origin feature/my-change`)
5. Open a pull request

Please keep the script dependency-free (standard library only) and compatible with Python 3.8+.

Found a bug or have an idea? [Open an issue](https://github.com/<your-username>/page-speed/issues).

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.
