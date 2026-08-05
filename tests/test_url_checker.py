"""Tests for pure parsing/loading logic in url_checker (no network)."""

import csv

from url_checker import CheckResult, load_urls, parse_sitemap

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/</loc></url>
  <url><loc>https://example.com/about</loc></url>
</urlset>
"""


def test_parse_sitemap():
    assert parse_sitemap(SITEMAP) == [
        "https://example.com/",
        "https://example.com/about",
    ]


def test_load_urls_csv_with_header(tmp_path):
    f = tmp_path / "urls.csv"
    f.write_text("url\nhttps://example.com/\nhttps://example.com/page\n", encoding="utf-8")
    assert load_urls(str(f)) == ["https://example.com/", "https://example.com/page"]


def test_load_urls_plain_list(tmp_path):
    f = tmp_path / "urls.txt"
    f.write_text("https://example.com/\n\nnot-a-url\nhttps://example.com/x\n", encoding="utf-8")
    assert load_urls(str(f)) == ["https://example.com/", "https://example.com/x"]


def test_load_urls_sitemap_file(tmp_path):
    f = tmp_path / "sitemap.xml"
    f.write_text(SITEMAP, encoding="utf-8")
    assert len(load_urls(str(f))) == 2


def test_result_ok_logic():
    ok = CheckResult(url="https://a.com", status=200, elapsed_ms=10, final_url="https://a.com")
    broken = CheckResult(url="https://a.com", status=404, elapsed_ms=10, final_url="https://a.com")
    errored = CheckResult(
        url="https://a.com", status=None, elapsed_ms=10, final_url="", error="TimeoutError"
    )
    assert ok.ok and not broken.ok and not errored.ok


def test_redirected_flag():
    r = CheckResult(
        url="https://a.com",
        status=200,
        elapsed_ms=10,
        final_url="https://a.com/new",
        redirect_chain=["https://a.com"],
    )
    assert r.redirected
