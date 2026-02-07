#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib

DATA = pathlib.Path("data/drive_essays.json")

MAPPING = {
    "Chinese (Singaporean)": "East Asian",
    "Chinese": "East Asian",
    "Western (English/European)": "White",
    "Russian/Eastern European": "White",
    "Sri Lankan Tamil": "South Asian",
    "Chinese (Hong Kong)": "East Asian",
    "Indian (Punjabi)": "South Asian",
    "Vietnamese": "East Asian",
    "Italian": "White",
    "Indian": "South Asian",
    "Indian (Bengali)": "South Asian",
    "Latino (Puerto Rican)": "Latine/Hispanic",
    "South Asian (Bengali)": "South Asian",
    "Czech": "White",
    "Indian (Tamil)": "South Asian",
    "Indian (Gujarati)": "South Asian",
    "Chinese/Taiwanese": "East Asian",
    "South Asian (Bangladeshi/Pakistani)": "South Asian",
    "Iranian/Persian": "Middle Eastern",
    "Spanish/Basque": "White",
    "Indian (Tamil/Malayalam)": "South Asian",
    "Indian (Malayali)": "South Asian",
    "Brazilian": "Latine/Hispanic",
    "Israeli/Hebrew": "Middle Eastern",
    "German": "White",
}


def main() -> int:
    records = json.loads(DATA.read_text())
    for record in records:
        origin = record.get("name_ethnic_origin")
        if origin:
            record["likely_ethnicity"] = MAPPING.get(origin, "Unknown")
        else:
            record["likely_ethnicity"] = "Unknown"
    DATA.write_text(json.dumps(records, indent=2))
    print("Added likely_ethnicity to", len(records), "records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
