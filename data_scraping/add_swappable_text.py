#!/usr/bin/env python3
"""Create swappable_text by replacing applicant name references with {name}."""

from __future__ import annotations

import json
import pathlib
import re

DATA = pathlib.Path("data/drive_essays.json")


def build_patterns(full: str | None, first: str | None, last: str | None):
    entries: list[tuple[re.Pattern[str], str]] = []

    def add_pattern(variant: str, placeholder: str):
        if not variant:
            return
        pattern = re.compile(rf"(?<!\\w){re.escape(variant)}(?!\\w)", re.IGNORECASE)
        entries.append((pattern, placeholder))

    def add_variants(value: str, placeholder: str):
        cleaned = value.strip()
        if not cleaned:
            return
        add_pattern(cleaned, placeholder)
        if "-" in cleaned:
            add_pattern(cleaned.replace("-", " "), placeholder)

    if first and last:
        first_clean = first.strip()
        last_clean = last.strip()
        if first_clean and last_clean:
            pattern = re.compile(
                rf"(?<!\\w){re.escape(first_clean)}(?:\s*\([^)]*\))?\s+{re.escape(last_clean)}(?!\\w)",
                re.IGNORECASE,
            )
            entries.append((pattern, "{full name}"))

    if full:
        add_variants(full, "{full name}")
    if first:
        add_variants(first, "{first name}")
    if last:
        add_variants(last, "{last name}")

    return entries


def replace_names(text: str, patterns):
    if not text:
        return text
    result = text
    for pattern, placeholder in patterns:
        result = pattern.sub(placeholder, result)
    return result


def main() -> int:
    records = json.loads(DATA.read_text())
    for record in records:
        patterns = build_patterns(
            record.get("applicant_name"),
            record.get("applicant_first_name"),
            record.get("applicant_last_name"),
        )
        record["swappable_text"] = replace_names(record.get("text", ""), patterns)
    DATA.write_text(json.dumps(records, indent=2))
    print("Updated swappable_text for", len(records), "records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
