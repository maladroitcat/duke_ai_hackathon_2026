#!/usr/bin/env python3
"""Extract text from scraped PDFs and combine with listing metadata."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
from typing import Dict, List

import spacy
from spacy.language import Language
from pdfminer.high_level import extract_text

DEFAULT_PDF_DIR = pathlib.Path("data/pdfs")
DEFAULT_METADATA = pathlib.Path("data/bachelors.json")
DEFAULT_OUTPUT = pathlib.Path("data/essays_from_pdfs.json")
DEFAULT_SPACY_MODEL = "en_core_web_sm"
STOPWORDS = {
    "essay",
    "sop",
    "statement",
    "success",
    "story",
    "public",
    "sample",
    "common",
    "app",
    "personal",
    "post",
    "grad",
    "masters",
    "bachelors",
    "bs",
    "ba",
    "ms",
    "phd",
    "mfa",
    "cs",
    "nlp",
    "ml",
    "ai",
    "engineering",
    "computer",
    "science",
    "undergrad",
    "auto",
}
PRONOUNS = {
    "female": [" she ", " her ", " hers "],
    "male": [" he ", " him ", " his "],
}


def clean_candidate_name(value: str) -> str | None:
    candidate = value.strip().strip(",.:-")
    if not candidate:
        return None
    if any(char.isdigit() for char in candidate):
        return None
    tokens = candidate.split()
    if not (1 <= len(tokens) <= 5):
        return None
    if all(token.istitle() or token.isupper() or "-" in token for token in tokens):
    return candidate


def name_from_source(source: str | None) -> str | None:
    if not source:
        return None
    match = re.search(r"\(([^()]+)\)", source)
    candidate = match.group(1) if match else source
    candidate = re.sub(r"public success story", "", candidate, flags=re.IGNORECASE)
    candidate = candidate.replace("\"", "").strip()
    return clean_candidate_name(candidate)
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse scraped PDFs into structured JSON")
    parser.add_argument(
        "--pdf-dir",
        type=pathlib.Path,
        default=DEFAULT_PDF_DIR,
        help=f"Directory that holds PDFs (default: {DEFAULT_PDF_DIR})",
    )
    parser.add_argument(
        "--metadata",
        type=pathlib.Path,
        default=DEFAULT_METADATA,
        help="Existing JSON metadata file with slug/school/program info",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--spacy-model",
        default=DEFAULT_SPACY_MODEL,
        help="spaCy model to load for PERSON extraction (default: en_core_web_sm)",
    )
    return parser.parse_args()


def load_metadata(path: pathlib.Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {entry.get("slug", ""): entry for entry in data if entry.get("slug")}


def guess_name(slug: str) -> str | None:
    tokens = [tok for tok in slug.split("-") if tok]
    if not tokens:
        return None
    filtered: List[str] = []
    for token in tokens:
        if re.search(r"\d", token):
            continue
        filtered.append(token)
    if not filtered:
        filtered = tokens
    name_tokens: List[str] = []
    for token in reversed(filtered):
        if token in STOPWORDS and name_tokens:
            break
        name_tokens.append(token)
    if not name_tokens:
        name_tokens = [filtered[-1]]
    raw = " ".join(reversed(name_tokens))
    cleaned = clean_candidate_name(raw.replace("_", " "))
    return cleaned.title() if cleaned else raw.replace("_", " ").title()


def extract_name_from_text(text: str, nlp: Language | None) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:20]:
        match = re.search(r"name\s*[:\-]\s*(.+)", line, re.IGNORECASE)
        if match:
            candidate = clean_candidate_name(match.group(1))
            if candidate:
                return candidate
        candidate = clean_candidate_name(line)
        if candidate and candidate.lower() not in STOPWORDS:
            return candidate
    if nlp:
        snippet = "\n".join(lines[:80]) or text[:6000]
        doc = nlp(snippet)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                candidate = clean_candidate_name(ent.text)
                if candidate:
                    return candidate
    return None


def split_name(full_name: str | None) -> tuple[str | None, str | None]:
    if not full_name:
        return None, None
    tokens = full_name.split()
    if not tokens:
        return None, None
    if len(tokens) == 1:
        return tokens[0], None
    return tokens[0], tokens[-1]


def infer_gender(text: str) -> str | None:
    lowered = f" {text.lower()} "
    scores = {key: sum(lowered.count(term) for term in terms) for key, terms in PRONOUNS.items()}
    if scores["female"] > scores["male"] and scores["female"] >= 2:
        return "female"
    if scores["male"] > scores["female"] and scores["male"] >= 2:
        return "male"
    return None


def extract_pdf_text(path: pathlib.Path) -> str:
    try:
        return extract_text(path)
    except Exception as exc:
        return f"<failed to parse PDF: {exc}>"


def normalize_text(raw: str) -> str:
    if not raw:
        return ""
    paragraphs: List[str] = []
    current: List[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(stripped)
    if current:
        paragraphs.append(" ".join(current))
    text = "\n\n".join(paragraphs)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def build_record(
    slug: str,
    pdf_path: pathlib.Path,
    text: str,
    metadata: Dict[str, str] | None,
    nlp: Language | None,
) -> Dict[str, str | None]:
    source_name = name_from_source(metadata.get("source")) if metadata else None
    text_name = extract_name_from_text(text, nlp)
    full_name = source_name or text_name or guess_name(slug)
    first_name, last_name = split_name(full_name)

    record = {
        "slug": slug,
        "source_pdf": str(pdf_path),
        "text": text.strip(),
        "applicant_name": full_name,
        "applicant_first_name": first_name,
        "applicant_last_name": last_name,
        "gender": infer_gender(text),
    }
    if metadata:
        record.update(
            {
                "school": metadata.get("school"),
                "program": metadata.get("program"),
                "programType": metadata.get("programType"),
                "source": metadata.get("source"),
                "downloadUrl": metadata.get("downloadUrl"),
            }
        )
    return record


def main() -> int:
    args = parse_args()
    if not args.pdf_dir.exists():
        print(f"PDF directory '{args.pdf_dir}' not found")
        return 1

    metadata = load_metadata(args.metadata)
    records: List[Dict[str, str | None]] = []

    try:
        nlp = spacy.load(args.spacy_model)
    except OSError:
        print(
            f"spaCy model '{args.spacy_model}' not found. Run 'python -m spacy download {args.spacy_model}'",
        )
        nlp = None

    for pdf_path in sorted(args.pdf_dir.glob("*.pdf")):
        slug = pdf_path.stem
        text = normalize_text(extract_pdf_text(pdf_path))
        record = build_record(slug, pdf_path, text, metadata.get(slug), nlp)
        records.append(record)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, indent=2))
    print(f"Wrote {len(records)} records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
