#!/usr/bin/env python3
"""Stage long-term arXiv artifacts in the private quantum-lab repository."""

from __future__ import annotations

import argparse
import gzip
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


STAMP_RE = re.compile(r"(\d{4})-(\d{2})-\d{2}")


def report_bucket(path: Path) -> tuple[str, str]:
    match = STAMP_RE.search(path.name)
    if match:
        return match.group(1), match.group(2)
    now = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return f"{now:%Y}", f"{now:%m}"


def copy_reports(source_root: Path, archive_root: Path) -> int:
    copied = 0
    if not source_root.is_dir():
        return copied

    for report in sorted(source_root.rglob("*")):
        if not report.is_file() or report.suffix.lower() not in {".html", ".md"}:
            continue
        year, month = report_bucket(report)
        source_name = report.parent.name
        fmt = "html" if report.suffix.lower() == ".html" else "markdown"
        destination = archive_root / "arxiv" / "reports" / year / month / fmt / source_name / report.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists() or report.read_bytes() != destination.read_bytes():
            shutil.copy2(report, destination)
            copied += 1
    return copied


def gzip_database(db_path: Path, archive_root: Path) -> list[Path]:
    if not db_path.is_file():
        return []

    now = datetime.now(timezone.utc)
    targets = [
        archive_root / "arxiv" / "backups" / "latest" / "daily_research_latest.sqlite.gz",
        archive_root / "arxiv" / "backups" / "monthly" / f"daily_research_{now:%Y-%m}.sqlite.gz",
    ]
    written: list[Path] = []
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        with db_path.open("rb") as src, gzip.open(target, "wb", compresslevel=9) as dst:
            shutil.copyfileobj(src, dst)
        written.append(target)
    return written


def ensure_readme(archive_root: Path) -> None:
    path = archive_root / "arxiv" / "README.md"
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """# ArXiv Private Archive

This directory is maintained by `arxiv-daily-researcher`.

```
arxiv/
├── backups/   # compressed SQLite snapshots for recovery
├── exports/   # JSON indexes for long-term search
└── reports/   # full HTML/Markdown report history grouped by year/month
```

The public website keeps only recent display artifacts. This private archive is
the long-term record for recovery, search, and research notes.
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--reports-root", type=Path, default=Path("data/reports/daily_research"))
    parser.add_argument("--db", type=Path, default=Path("data/daily_research/daily_research.db"))
    args = parser.parse_args()

    args.archive_root.mkdir(parents=True, exist_ok=True)
    ensure_readme(args.archive_root)
    report_count = copy_reports(args.reports_root, args.archive_root)
    backup_paths = gzip_database(args.db, args.archive_root)
    print(f"archived reports: {report_count}")
    for path in backup_paths:
        print(f"database backup written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
