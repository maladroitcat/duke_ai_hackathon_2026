"""Generate recommendation letters using Latin square design.

Each variable value appears exactly once per demographic group,
with shifted indices ensuring adj_1 != adj_2 and trait_1 != trait_2.
Result: 5 combos x 2 templates x 6 groups = 60 letters.
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VARIABLES_DIR = ROOT / "templates" / "variables"
LETTERS_DIR = ROOT / "templates" / "letters"
OUTPUT_DIR = ROOT / "data" / "generated_letters"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Load CSVs ---
def load_csv(filename):
    with open(VARIABLES_DIR / filename) as f:
        return list(csv.DictReader(f))

names = load_csv("names.csv")
adjectives = load_csv("adjectives.csv")
traits = load_csv("traits.csv")
extracurriculars = load_csv("extracurriculars.csv")
pronouns = {row["gender"]: row for row in load_csv("pronouns.csv")}

# --- Load templates ---
# Import templates by reading the .py files as text and extracting the string
def load_template(filename):
    text = (LETTERS_DIR / filename).read_text()
    # Extract the string between triple quotes
    start = text.index('"""') + 3
    end = text.index('"""', start)
    return text[start:end]

template_v1 = load_template("letter_template_v1.py")
template_v2 = load_template("letter_template_v2.py")
templates = {"v1": template_v1, "v2": template_v2}

# --- Group variables by (race, gender) ---
def group_by_demo(rows, value_key):
    groups = {}
    for row in rows:
        key = (row["race"], row["gender"])
        groups.setdefault(key, []).append(row[value_key])
    return groups

name_groups = group_by_demo(names, "name")
adj_groups = group_by_demo(adjectives, "adjective")
trait_groups = group_by_demo(traits, "trait")
ec_groups = group_by_demo(extracurriculars, "extracurricular")

# --- Latin square generation ---
# For each demographic group (5 values per variable), create 5 rows.
# Each row i uses index i for each variable, with adj_2 and trait_2
# shifted by 1 so they never collide with adj_1 and trait_1.
#
#   row i:  name[i], adj[i], adj[(i+1)%5], trait[i], trait[(i+1)%5], ec[i]

N = 5  # values per variable per group
all_letters = []
letter_id = 0

for (race, gender) in sorted(name_groups):
    p = pronouns[gender]
    ns = name_groups[(race, gender)]
    adjs = adj_groups[(race, gender)]
    trs = trait_groups[(race, gender)]
    ecs = ec_groups[(race, gender)]

    for i in range(N):
        for tmpl_name, tmpl in templates.items():
            letter_id += 1
            filled = tmpl.format(
                name=ns[i],
                pronoun_subject=p["pronoun_subject"],
                pronoun_object=p["pronoun_object"],
                pronoun_possessive=p["pronoun_possessive"],
                adj_1=adjs[i],
                adj_2=adjs[(i + 1) % N],
                trait_1=trs[i],
                trait_2=trs[(i + 1) % N],
                extracurricular=ecs[i],
                teacher_name="Ms. Johnson",
            )
            all_letters.append({
                "id": letter_id,
                "template": tmpl_name,
                "race": race,
                "gender": gender,
                "name": ns[i],
                "adj_1": adjs[i],
                "adj_2": adjs[(i + 1) % N],
                "trait_1": trs[i],
                "trait_2": trs[(i + 1) % N],
                "extracurricular": ecs[i],
                "letter": filled.strip(),
            })

# --- Write output ---
output_path = OUTPUT_DIR / "letters.json"
with open(output_path, "w") as f:
    json.dump(all_letters, f, indent=2)

# Summary
from collections import Counter
demo_counts = Counter((l["race"], l["gender"]) for l in all_letters)
print(f"Total letters generated: {len(all_letters)}")
print("Breakdown by (race, gender):")
for (race, gender), count in sorted(demo_counts.items()):
    print(f"  {race:6s} {gender:6s}: {count}")
