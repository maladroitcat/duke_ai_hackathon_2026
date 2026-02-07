"""Generate radar charts of LLM scoring by race (women only)."""

import json
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent
scores_file = sys.argv[1] if len(sys.argv) > 1 else "scores.json"
output_file = sys.argv[2] if len(sys.argv) > 2 else "radar_by_race.png"
SCORES_PATH = ROOT / "data" / scores_file
OUTPUT_PATH = ROOT / "results" / output_file

CATEGORIES = ["grammar", "extracurricular_score", "overall_admissibility"]
CATEGORY_LABELS = ["Grammar", "Extracurricular", "Overall\nAdmissibility"]
RACE_COLORS = {"black": "#E24A33", "white": "#348ABD", "asian": "#988ED5"}


def main():
    scores = json.load(open(SCORES_PATH))

    # Filter to women only, skip errors
    scores = [s for s in scores if s["gender"] == "female" and "error" not in s]

    # Group: model -> race -> list of score dicts
    grouped = defaultdict(lambda: defaultdict(list))
    for s in scores:
        grouped[s["model"]][s["race"]].append(s)

    models = sorted(grouped.keys())
    races = sorted(RACE_COLORS.keys())
    n_models = len(models)

    # Radar setup
    angles = np.linspace(0, 2 * np.pi, len(CATEGORIES), endpoint=False).tolist()
    angles += angles[:1]  # close the polygon

    fig, axes = plt.subplots(1, n_models, figsize=(5 * n_models, 5),
                              subplot_kw=dict(polar=True))
    if n_models == 1:
        axes = [axes]

    fig.suptitle("Admissions Scoring by Race (Women Only)", fontsize=16, y=1.02)

    for ax, model in zip(axes, models):
        ax.set_title(model.split("/")[-1], fontsize=10, pad=20)
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7, color="grey")
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(CATEGORY_LABELS, fontsize=9)

        for race in races:
            entries = grouped[model][race]
            if not entries:
                continue
            means = []
            for cat in CATEGORIES:
                vals = [e[cat] for e in entries if e.get(cat) is not None]
                means.append(np.mean(vals) if vals else 0)
            means += means[:1]  # close polygon

            ax.plot(angles, means, "o-", linewidth=2, label=race.capitalize(),
                    color=RACE_COLORS[race], markersize=4)
            ax.fill(angles, means, alpha=0.1, color=RACE_COLORS[race])

        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=8)

    plt.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=150, bbox_inches="tight")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
