#!/usr/bin/env python3
"""Assign likely_gender based on pronouns and first name heuristics."""

from __future__ import annotations

import json
import pathlib

DATA = pathlib.Path("data/drive_essays.json")

FEMALE_PRONOUNS = [" she ", " her ", " hers ", " herself "]
MALE_PRONOUNS = [" he ", " him ", " his ", " himself "]

NAME_GENDER = {
    "alexander": "male",
    "alisa": "female",
    "ananya": "female",
    "anjali": "female",
    "anna": "female",
    "arka": "male",
    "ava": "female",
    "chanwoo": "male",
    "charles": "male",
    "chenghao": "male",
    "chenglei": "male",
    "chenyang": "male",
    "daman": "male",
    "daneshvar": "male",
    "deepak": "male",
    "emmanuel": "male",
    "fatima": "female",
    "frieda": "female",
    "hancheng": "male",
    "himanshu": "male",
    "iñigo": "male",
    "iigo": "male",
    "inderjeet": "male",
    "jatin": "male",
    "jayroop": "male",
    "joel": "male",
    "krithika": "female",
    "leo": "male",
    "luiza": "female",
    "lunyiu": "male",
    "mahyar": "male",
    "mayank": "male",
    "mayanak": "male",
    "ofir": "male",
    "paul": "male",
    "prateksha": "female",
    "pretha": "female",
    "qing": "male",
    "quang": "male",
    "rachit": "male",
    "rishi": "male",
    "robert": "male",
    "rui-jie": "female",
    "ryan": "male",
    "saarth": "male",
    "sarthak": "male",
    "seungone": "male",
    "sewon": "male",
    "shangyin": "male",
    "shikhar": "male",
    "shreyas": "male",
    "shuyan": "female",
    "siddartha": "male",
    "siddharth": "male",
    "soumitri": "male",
    "sukwon": "male",
    "sweta": "female",
    "tim": "male",
    "vilém": "male",
    "vilã©m": "male",
    "xiaochen": "male",
    "yash": "male",
    "yong": "male",
    "yuxuan": "male",
    "zexuan": "male",
    "zhiyuan": "male",
    "leo": "male",
    "lunyiu": "male",
    "ruijie": "female",
}


def main() -> int:
    records = json.loads(DATA.read_text())
    for record in records:
        text = f" {record.get('text', '').lower()} "
        female_score = sum(text.count(token) for token in FEMALE_PRONOUNS)
        male_score = sum(text.count(token) for token in MALE_PRONOUNS)
        name = (record.get("applicant_first_name") or "").lower()
        if name in NAME_GENDER:
            record["likely_gender"] = NAME_GENDER[name]
        elif female_score > male_score and female_score >= 2:
            record["likely_gender"] = "female"
        elif male_score > female_score and male_score >= 2:
            record["likely_gender"] = "male"
        else:
            record["likely_gender"] = "unknown"
    DATA.write_text(json.dumps(records, indent=2))
    print("Updated likely_gender for", len(records), "records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
