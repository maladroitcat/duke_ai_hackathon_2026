#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib

DATA = pathlib.Path("data/drive_essays.json")

ORIGINS = {
    "brown-phd-sop-essay-rui-jie": "Chinese (Singaporean)",
    "brown-phd-sop-essay-yong-zheng-xin": "Chinese",
    "caltech-phd-sop-essay-robert-2024": "Western (English/European)",
    "cmu-phd-nlp-ml-sop-essay-paul-2024": "Chinese",
    "cmu-phd-nlp-sop-essay-seungone-kim": "Korean",
    "cmu-phd-nlp-sop-essay-shikhar-2024": "Indian",
    "cmu-phd-security-cryptography-sop-alexander-2024": "Russian/Eastern European",
    "cmu-phd-sop-anjali-essay": "Sri Lankan Tamil",
    "cmu-phd-sop-essay-ava-2024": "Chinese (Hong Kong)",
    "cmu-phd-sop-essay-daman-arora-2024": "Indian (Punjabi)",
    "cmu-phd-sop-essay-qing-xiao": "Chinese",
    "cmu-phd-sop-essay-shuyan-zhou-2024": "Chinese",
    "cmu-phd-theory-cryptography-security-sop-essay-quang-2024": "Vietnamese",
    "columbia-phd-sop-essay-anna-vannucci": "Italian",
    "columbia-phd-sop-essay-shreyas-2024": "Indian",
    "columbia-phd-sop-essay-sweta-karlekar": "Indian",
    "cornell-phd-sop-essay-emmanuel-2024": "Latino (Puerto Rican)",
    "deakin-phd-sop-essay-pretha-2024": "South Asian (Bengali)",
    "eth-phd-sop-essay-vilem-zouhar-2024": "Czech",
    "gatech-phd-sop-essay-chenyang-zhang": "Chinese",
    "harvard-phd-sop-essay-rachit-2024": "Indian",
    "ist-phd-sop-essay-mahyar-karimi": "Iranian/Persian",
    "jhu-phd-nlp-sop-essay-krithika-2024": "Indian (Tamil)",
    "jhu-phd-sop-essay-yash-mehta": "Indian (Gujarati)",
    "mit-phd-sop-essay-chanwoo-park": "Korean",
    "mit-phd-sop-essay-charles-lu-2024": "Chinese",
    "mit-phd-sop-essay-ryan-2024": "Chinese/Taiwanese",
    "mit-phd-sop-essay-siddharth-2024": "Indian",
    "mit-phd-sop-essay-xiaochen-zhu": "Chinese",
    "nyu-phd-sop-essay-jatin-2024": "Indian",
    "oxford-phd-sop-essay-jayroop-2024": "Indian",
    "princeton-phd-sop-essay-zexuan-zhong": "Chinese",
    "rit-phd-nlp-sop-essay-arka-2024": "Indian (Bengali)",
    "rutgers-phd-nlp-responsible-ai-sop-essay-fatima-2024": "South Asian (Bangladeshi/Pakistani)",
    "stanford-phd-hci-data-science-sop-essay-hancheng-cao": "Chinese",
    "stanford-phd-nlp-sop-essay-chenglei-si": "Chinese",
    "stanford-phd-sop-essay-daneshvar-2024": "Iranian/Persian",
    "stanford-phd-sop-essay-frieda-2024": "Chinese",
    "stanford-phd-sop-essay-rishi-2024": "Indian",
    "ucb-phd-sop-essay-himanshu-2024": "Indian",
    "ucb-phd-sop-essay-inigo-parra-2024": "Spanish/Basque",
    "ucb-phd-sop-essay-shangyin-tan": "Chinese",
    "uchicago-phd-nlp-ml-sop-essay-chenghao-2024": "Chinese",
    "ucsb-phd-nlp-ml-sop-essay-deepak-2024": "Indian",
    "uiuc-phd-sop-essay-sarthak-2024": "Indian",
    "uiuc-phd-theory-cryptography-sop-ananya-essay": "Indian",
    "um-phd-swe-sop-essay-yuxuan-jiang": "Chinese",
    "umd-phd-sop-essay-prateksha-udhayanan-2024": "Indian (Tamil/Malayalam)",
    "umich-phd-sop-essay-inderjeet-2024": "Indian (Malayali)",
    "unc-phd-sop-essay-soumitri-2024": "Indian (Bengali)",
    "unc-phd-sop-essay-sukwon-2024": "Korean",
    "upenn-phd-sop-essay-mayank-2024": "Indian",
    "usc-phd-sop-essay-siddartha-devic": "Indian",
    "uta-phd-nlp-ml-sop-essay-zeyu-leo-liu": "Chinese",
    "uta-phd-sop-essay-lunyiu-nie": "Chinese",
    "uta-phd-sop-essay-saarth-2024": "Indian",
    "uw-phd-nlp-ml-sop-essay-luiza-2024": "Brazilian",
    "uw-phd-nlp-ml-sop-essay-ofir-press": "Israeli/Hebrew",
    "uw-phd-nlp-sop-essay-ananya-2024": "Indian",
    "uw-phd-nlp-sop-essay-joel-jang": "Korean",
    "uw-phd-nlp-sop-essay-sewon-min-2024": "Korean",
    "uw-phd-nlp-sop-essay-tim-dettmers": "German",
    "uw-phd-sop-essay-alisa-2024": "Chinese",
    "uw-phd-sop-essay-zhiyuan-zeng": "Chinese",
    "usc-phd-sop-essay-siddartha-devic": "Indian",
    "cmu-phd-sop-essay-shuyan-zhou-2024": "Chinese",
    "cmu-phd-sop-essay-qing-xiao": "Chinese",
    "uta-phd-nlp-ml-sop-essay-zeyu-leo-liu": "Chinese",
}


def main() -> int:
    if not DATA.exists():
        raise SystemExit(f"Missing {DATA}")
    records = json.loads(DATA.read_text())
    updated = 0
    for record in records:
        slug = record.get("slug")
        origin = ORIGINS.get(slug)
        if origin:
            record["name_ethnic_origin"] = origin
            updated += 1
        else:
            record.setdefault("name_ethnic_origin", None)
    DATA.write_text(json.dumps(records, indent=2))
    print(f"Applied origins to {updated} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
