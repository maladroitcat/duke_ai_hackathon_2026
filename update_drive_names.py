#!/usr/bin/env python3
"""Rewrite data/drive_essays.json with authoritative names from metadata/text."""

from __future__ import annotations

import json
import pathlib
import re
from typing import Dict, List, Tuple

DRIVE_JSON = pathlib.Path("data/drive_essays.json")
METADATA_JSON = pathlib.Path("data/bachelors.json")
STOPWORDS = {
    "statement",
    "purpose",
    "essay",
    "university",
    "college",
    "computer",
    "science",
    "program",
    "common",
    "app",
    "my",
}


def load_json(path: pathlib.Path):
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")
    return json.loads(path.read_text())


def extract_name_from_source(source: str | None) -> str | None:
    if not source:
        return None
    match = re.search(r"\(([^()]+)\)", source)
    candidate = match.group(1) if match else source
    candidate = re.sub(r"public success story", "", candidate, flags=re.IGNORECASE)
    candidate = candidate.replace("\"", "").strip()
    return candidate or None


def guess_from_slug(slug: str | None) -> str | None:
    if not slug:
        return None
    tokens = [tok for tok in slug.split("-") if tok]
    if not tokens:
        return None
    tail = []
    for token in reversed(tokens):
        if any(char.isdigit() for char in token):
            continue
        if token in STOPWORDS and tail:
            break
        tail.append(token)
    if not tail:
        tail = tokens[-2:]
    name = " ".join(reversed(tail))
    return name.replace("_", " ").title()


def candidate_from_text(text: str, seed: str | None) -> str | None:
    if not text:
        return None
    snippet = text[:1500]
    pattern = re.compile(r"([A-Z][A-Za-z\-']+(?:\s+[A-Z][A-Za-z\-']+){1,3})")
    lower_seed = seed.lower() if seed else None
    for match in pattern.finditer(snippet):
        candidate = match.group(1).strip()
        candidate = " ".join(candidate.split())
        tokens = candidate.split()
        if not (2 <= len(tokens) <= 4):
            continue
        while tokens and tokens[-1].lower() in STOPWORDS:
            tokens.pop()
        if len(tokens) < 2:
            continue
        if any(token.lower() in STOPWORDS for token in tokens):
            continue
        if lower_seed and lower_seed not in [tok.lower() for tok in tokens]:
            continue
        return " ".join(tokens)
    return None


def split_name(full_name: str | None) -> Tuple[str | None, str | None]:
    if not full_name:
        return None, None
    tokens = [tok for tok in full_name.split() if tok]
    if not tokens:
        return None, None
    if len(tokens) == 1:
        return tokens[0], None
    return tokens[0], tokens[-1]


def main() -> int:
    records: List[Dict[str, object]] = load_json(DRIVE_JSON)
    meta = {entry["slug"]: entry for entry in load_json(METADATA_JSON)}

    updated = 0
    for record in records:
        slug = record.get("slug")
        meta_entry = meta.get(slug, {})
        source_name = extract_name_from_source(meta_entry.get("source"))
        text = record.get("text", "")
        text_name = candidate_from_text(text, source_name.split()[0] if source_name else None)
        fallback = guess_from_slug(slug)
        full_name = text_name or source_name or fallback or record.get("applicant_name")
        first, last = split_name(full_name)
        record["applicant_name"] = full_name
        record["applicant_first_name"] = first
        record["applicant_last_name"] = last
        updated += 1

    DRIVE_JSON.write_text(json.dumps(records, indent=2))
    print(f"Updated {updated} records in {DRIVE_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
