#!/usr/bin/env python3
"""生成每日论文动态的静态 index.html（列出 site_dir/reports 下所有 HTML 报告）。

用法: python scripts/build_site_index.py <site_dir>
"""
import argparse, html, re, sys
from datetime import datetime, timezone
from pathlib import Path

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

def report_source(p: Path) -> str:
    stem = p.stem
    return stem.split("_Report_", 1)[0] if "_Report_" in stem else stem

def report_date(p: Path) -> str:
    m = DATE_RE.search(p.name)
    return m.group(1) if m else datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("site_dir", type=Path)
    args = ap.parse_args()
    site = args.site_dir.resolve()
    reports_dir = site / "reports"
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
 :root {{ color-scheme: light dark; }}
 body {{ font-family: -apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
        max-width: 920px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6;
        background:#fff; color:#1a1a1a; }}
 h1 {{ font-size:1.5rem; }}
 .meta {{ color:#777; font-size:.85rem; margin-bottom:1rem; }}
 ul {{ list-style:none; padding:0; }}
 li {{ padding:.55rem .25rem; border-bottom:1px solid #eee; font-size:.95rem; }}
 li a {{ word-break:break-all; }}
 .d {{ display:inline-block; min-width:6.5rem; color:#0b5cad; font-variant-numeric:tabular-nums; }}
 .s {{ display:inline-block; min-width:4rem; color:#555; }}
 a {{ color:#0b5cad; text-decoration:none; }}
 a:hover {{ text-decoration:underline; }}
 .back {{ margin-top:1.2rem; }}
 @media (prefers-color-scheme: dark) {{
   body {{ background:#222; color:#e5e7eb; }}
   a, .d {{ color:#60a5fa; }}
   .s, .meta {{ color:#9ca3af; }}
   li {{ border-bottom-color:#3f3f3f; }}
 }}
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
