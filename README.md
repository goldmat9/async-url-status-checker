# Async URL Status Checker

[![CI](https://github.com/goldmat9/async-url-status-checker/actions/workflows/ci.yml/badge.svg)](https://github.com/goldmat9/async-url-status-checker/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)

Blazing-fast bulk URL auditing from the command line. Feed it a CSV of URLs or an XML sitemap — it checks thousands of URLs concurrently with `asyncio` + `aiohttp`, maps full redirect chains, flags broken links, measures response times, and writes a clean CSV report.

Built for technical SEO audits, site migrations, and large-scale link validation where synchronous checkers (or manual crawling) are way too slow.

<!-- TODO: add a 10-second demo GIF here — record one run against a real sitemap -->

## Features

- **Concurrent by design** — checks hundreds of URLs in seconds with a configurable concurrency limit
- **Sitemap input** — point it directly at `sitemap.xml` (local file or live URL), no preprocessing
- **Full redirect chains** — records every hop, not just the final status
- **Broken-link report** — 4xx/5xx, timeouts, DNS and connection errors, exported to CSV
- **Response-time stats** — median and max latency per run

## Install

```bash
pip install -r requirements.txt
```

Requires Python 3.10+.

## Usage

```bash
# Check a CSV of URLs (one per line, or a `url` column)
python url_checker.py urls.csv

# Check an entire live sitemap
python url_checker.py https://example.com/sitemap.xml

# Tune concurrency, timeout, and output
python url_checker.py urls.csv --concurrency 50 --timeout 15 -o report.csv
```

Example output:

```
Checking 1,240 URLs (concurrency=20)...

Checked 1240 URLs
  OK (2xx/3xx):      1197
  Broken/errored:    43
  With redirects:    86
  Response time:     median 212 ms, max 4810 ms

Broken / errored URLs:
  [HTTP 404] https://example.com/old-landing-page
  [ClientConnectorError: ...] https://example.com/typo-page
  ...

Full report written to url_report.csv
```

## Why not X?

- **Screaming Frog / Sitebulb** — excellent crawlers, but heavy and license-gated for a quick 5,000-URL status check. This is a 10-second terminal command, scriptable and CI-friendly.
- **`requests` + a for loop** — synchronous; checking 1,000 URLs takes minutes instead of seconds. This project shows the `asyncio`/`aiohttp` pattern done properly.
- **Online broken-link checkers** — capped, slow, and you can't run them against staging or behind auth.

## Use cases

- Post-migration redirect validation (did every old URL land on a 200?)
- Pre-launch sitemap audits
- Recurring broken-link monitoring in CI or a scheduled job
- Affiliate/outbound link hygiene checks on large content sites

## Roadmap

- [ ] Retry logic with backoff for flaky hosts
- [ ] Optional per-domain rate limiting
- [ ] HTML report with redirect-chain visualization
- [ ] `--header` flag for auth/cookies on staging environments

## Contributing

Issues and PRs welcome — especially real-world edge cases (weird sitemaps, redirect loops, unusual status codes).

## License

MIT — see [LICENSE](LICENSE).
