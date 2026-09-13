#!/usr/bin/env python3
"""Build the public arXiv report index for the Hexo site.

The site repository is a public display surface, so this helper can also prune
old HTML reports before rebuilding the index. Long-term history belongs in the
private archive repository.
"""

import argparse
import html
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def report_source(p: Path) -> str:
    stem = p.stem
    return stem.split("_Report_", 1)[0] if "_Report_" in stem else stem


def report_date(p: Path) -> str:
    m = DATE_RE.search(p.name)
    return m.group(1) if m else datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")


def report_datetime(p: Path) -> datetime:
    date_text = report_date(p)
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)


def prune_reports(reports_dir: Path, max_age_days: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    removed = 0
    for path in reports_dir.rglob("*.html"):
        if report_datetime(path) < cutoff:
            path.unlink()
            removed += 1
    for directory in sorted(
        (p for p in reports_dir.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True,
    ):
        try:
            directory.rmdir()
        except OSError:
            pass
    return removed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("site_dir", type=Path)
    ap.add_argument(
        "--max-age-days",
        type=int,
        default=None,
        help="Prune public HTML reports older than this many days before indexing.",
    )
    args = ap.parse_args()

    site = args.site_dir.resolve()
    reports_dir = site / "reports"
    if reports_dir.is_dir() and args.max_age_days is not None:
        removed = prune_reports(reports_dir, args.max_age_days)
        print(f"pruned {removed} old public reports")

    reports = sorted(reports_dir.rglob("*.html")) if reports_dir.is_dir() else []
    rows = [(report_date(p), report_source(p), p.relative_to(site).as_posix())
            for p in sorted(reports, key=lambda x: x.name, reverse=True)]
    items = "\n".join(
        f'<li><span class="d">{html.escape(d)}</span>'
        f'<span class="s">{html.escape(s)}</span>'
        f'<a href="{html.escape(rel)}">{html.escape(rel)}</a></li>'
        for d, s, rel in rows)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>论文动态</title>
<style>
 body {{ font-family: -apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
        max-width: 920px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6;
        background:#222; color:#e5e7eb; }}
 h1 {{ font-size:1.5rem; }}
 .meta {{ color:#9ca3af; font-size:.85rem; margin-bottom:1rem; }}
 ul {{ list-style:none; padding:0; }}
 li {{ padding:.55rem .25rem; border-bottom:1px solid #3f3f3f; font-size:.95rem; }}
 li a {{ word-break:break-all; }}
 .d {{ display:inline-block; min-width:6.5rem; color:#60a5fa; font-variant-numeric:tabular-nums; }}
 .s {{ display:inline-block; min-width:4rem; color:#9ca3af; }}
 a {{ color:#60a5fa; text-decoration:none; }}
 a:hover {{ text-decoration:underline; }}
 .back {{ margin-top:1.2rem; }}
</style>
</head>
<body>
<h1>论文动态</h1>
<p class="meta">由 ArXiv Daily Researcher 自动生成 · 共 {len(rows)} 份报告 · 更新于 {now}</p>
<ul>
{items}
</ul>
<p class="back"><a href="/">← 返回首页</a></p>
</body>
</html>
"""
    (site / "index.html").write_text(doc, encoding="utf-8")
    print(f"index.html written: {len(rows)} reports")
    return 0


if __name__ == "__main__":
    sys.exit(main())
