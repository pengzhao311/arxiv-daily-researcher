#!/usr/bin/env python3
"""Export a searchable paper index from the SQLite research ledger.

The JSON output is intentionally text-based and stable enough for Git storage.
Use ``--visibility public`` for the website index and ``private`` for the lab
archive.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def decode_json(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def first_present(payload: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return default


def normalize_authors(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def normalize_keywords(score: dict[str, Any]) -> list[str]:
    candidates = (
        score.get("matched_keywords"),
        score.get("keywords"),
        score.get("extracted_keywords"),
    )
    for value in candidates:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, dict):
            return [str(key).strip() for key in value if str(key).strip()]
    return []


def score_value(score: dict[str, Any]) -> float | None:
    for key in ("total_score", "score", "ranking_score", "core_relevance_score"):
        value = score.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                pass
    return None


def normalize_report_path(value: Any) -> str:
    text = str(value or "").strip()
    marker = "/data/reports/"
    if marker in text:
        return "data/reports/" + text.split(marker, 1)[1]
    return text


def export_rows(db_path: Path, visibility: str) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                papers.source,
                papers.paper_id,
                papers.canonical_id,
                papers.version,
                papers.paper_json,
                papers.score_json,
                papers.abstract_cn,
                papers.analysis_json,
                papers.completed_at,
                deliveries.report_path,
                deliveries.report_at,
                deliveries.delivered_at
            FROM paper_deliveries AS deliveries
            JOIN daily_papers AS papers
              ON papers.source = deliveries.source
             AND papers.paper_id = deliveries.paper_id
            ORDER BY COALESCE(deliveries.report_at, deliveries.delivered_at) DESC,
                     papers.source ASC,
                     papers.canonical_id ASC,
                     papers.version DESC
            """
        ).fetchall()
    finally:
        conn.close()

    exported: list[dict[str, Any]] = []
    for row in rows:
        paper = decode_json(row["paper_json"], {})
        score = decode_json(row["score_json"], {})
        analysis = decode_json(row["analysis_json"], {})
        item = {
            "source": row["source"],
            "paper_id": row["paper_id"],
            "canonical_id": row["canonical_id"],
            "version": row["version"],
            "title": first_present(paper, "title"),
            "authors": normalize_authors(first_present(paper, "authors", "author", default=[])),
            "published": first_present(paper, "published", "published_date", "date"),
            "updated": first_present(paper, "updated", "updated_date"),
            "categories": first_present(paper, "categories", default=[]),
            "arxiv_id": first_present(paper, "arxiv_id", default=row["canonical_id"]),
            "url": first_present(paper, "url", "arxiv_url"),
            "pdf_url": first_present(paper, "pdf_url"),
            "score": score_value(score),
            "qualified": bool(score.get("qualified", score.get("is_qualified", False))),
            "keywords": normalize_keywords(score),
            "tldr": first_present(paper, "semantic_scholar_tldr", "tldr"),
            "report_path": normalize_report_path(row["report_path"]),
            "report_at": row["report_at"],
            "delivered_at": row["delivered_at"],
        }
        if visibility == "private":
            item["abstract"] = first_present(paper, "abstract")
            item["abstract_cn"] = row["abstract_cn"] or ""
            item["score_detail"] = score
            item["analysis"] = analysis
        exported.append(item)
    return exported


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/daily_research/daily_research.db"),
        help="Path to daily_research.db.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--visibility",
        choices=("public", "private"),
        default="public",
        help="Public keeps only display/search fields; private includes analysis detail.",
    )
    args = parser.parse_args()

    if not args.db.is_file():
        raise SystemExit(f"database not found: {args.db}")

    papers = export_rows(args.db, args.visibility)
    payload = {
        "schema_version": 1,
        "visibility": args.visibility,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "paper_count": len(papers),
        "papers": papers,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"paper index written: {args.output} ({len(papers)} papers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
