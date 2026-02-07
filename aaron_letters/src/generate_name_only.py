"""Generate letters varying ONLY the student name. All other variables held constant."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VARIABLES_DIR = ROOT / "templates" / "variables"
LETTERS_DIR = ROOT / "templates" / "letters"
OUTPUT_DIR = ROOT / "data" / "generated_letters"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_csv(filename):
    with open(VARIABLES_DIR / filename) as f:
        return list(csv.DictReader(f))


def load_template(filename):
    text = (LETTERS_DIR / filename).read_text()
    start = text.index('"""') + 3
    end = text.index('"""', start)
    return text[start:end]


# Fixed variables: first row from each file
adj_1 = load_csv("adjectives.csv")[0]["adjective"]
adj_2 = load_csv("adjectives.csv")[1]["adjective"]
trait_1 = load_csv("traits.csv")[0]["trait"]
trait_2 = load_csv("traits.csv")[1]["trait"]
extracurricular = load_csv("extracurriculars.csv")[0]["extracurricular"]

print(f"Fixed variables:")
print(f"  adj_1: {adj_1}")
print(f"  adj_2: {adj_2}")
print(f"  trait_1: {trait_1}")
print(f"  trait_2: {trait_2}")
print(f"  extracurricular: {extracurricular}")
print()

names = load_csv("names.csv")
pronouns = {row["gender"]: row for row in load_csv("pronouns.csv")}
templates = {
    "v1": load_template("letter_template_v1.py"),
    "v2": load_template("letter_template_v2.py"),
}

all_letters = []
letter_id = 0

for row in names:
    p = pronouns[row["gender"]]
    for tmpl_name, tmpl in templates.items():
        letter_id += 1
        filled = tmpl.format(
            name=row["name"],
            pronoun_subject=p["pronoun_subject"],
            pronoun_object=p["pronoun_object"],
            pronoun_possessive=p["pronoun_possessive"],
            adj_1=adj_1,
            adj_2=adj_2,
            trait_1=trait_1,
            trait_2=trait_2,
            extracurricular=extracurricular,
            teacher_name="Ms. Johnson",
        )
        all_letters.append({
            "id": letter_id,
            "template": tmpl_name,
            "race": row["race"],
            "gender": row["gender"],
            "name": row["name"],
            "adj_1": adj_1,
            "adj_2": adj_2,
            "trait_1": trait_1,
            "trait_2": trait_2,
            "extracurricular": extracurricular,
            "letter": filled.strip(),
        })

output_path = OUTPUT_DIR / "letters_name_only.json"
with open(output_path, "w") as f:
    json.dump(all_letters, f, indent=2)

print(f"Generated {len(all_letters)} letters (name-only variation)")
print(f"  {len(names)} names x {len(templates)} templates")
print(f"Saved to {output_path}")
