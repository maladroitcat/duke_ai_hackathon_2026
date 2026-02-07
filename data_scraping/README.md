# Measuring Demographic Bias in LLM-Based Admissions Scoring

This project investigates whether small language models exhibit racial and gender bias when scoring college application materials. It was built for the Duke AI Hackathon 2026.

## Approach

We use three complementary data pipelines to test for bias:

1. **Synthetic application materials** — Template-based recommendation letters and personal essays generated via Latin square design so that every variable value (name, trait, hometown, extracurricular, etc.) appears exactly once per demographic group. This controls for content quality and isolates the effect of demographic signals.

2. **Name-only variation** — The same template letter with all variables held constant except the applicant's name. This is the cleanest test: identical text, different name.

3. **Real essays with name swaps** — Actual admissions essays scraped from [OpenEssays.org](https://openessays.org) and Google Drive, with applicant names replaced by demographically-coded names from a lookup table. This tests whether bias persists on natural (non-template) writing.

Each set of materials is scored by multiple small LLMs via the [OpenRouter](https://openrouter.ai/) API on a 0-100 rubric (grammar, tone, academic readiness, life context). We then compare mean scores and compute Cohen's d effect sizes across race (Asian, Black, White) and gender (female, male) groups.

### Prompt variants

Three system-prompt strategies are tested to see if framing changes bias:

| Variant | Description |
|---------|-------------|
| **Original** | Standard admissions evaluator prompt with rubric |
| **Debiased** | Same rubric + explicit instruction to ignore demographic signals |
| **Metadata** | Same rubric, but candidate race/gender are provided explicitly |

A fourth **simple** prompt (single 0-100 "should this applicant be admitted?" score) is compared against the rubric-based prompt to measure how scoring granularity affects bias.

## Models tested

All models are accessed through OpenRouter:

- `meta-llama/llama-3.1-8b-instruct`
- `google/gemma-2-9b-it`
- `mistralai/mistral-7b-instruct-v0.3`
- `microsoft/phi-4`
- `qwen/qwen-2.5-7b-instruct`
- `x-ai/grok-3-mini`

## Repository structure

```
.
├── README.md
├── requirements.txt
├── credentials.example.json
├── openrouter_client.py          # Generic OpenRouter chat helper
├── openessays_scraper.py         # Scrape essays from openessays.org + external sources
├── pdf_to_json.py                # Extract text from Google Drive PDFs
├── add_swappable_text.py         # Replace real names with {name} placeholders
├── add_likely_ethnicity.py       # Map name origins → broad ethnicity categories
├── assign_likely_gender.py       # Infer gender from pronouns / first name
├── assign_name_origins.py        # Classify name ethnic origins via LLM
├── update_drive_names.py         # Fix/normalize names in drive essay data
│
├── aaron_letters/                # Core experiment pipeline
│   ├── .env                      # OPENROUTER_API_KEY (not committed)
│   ├── templates/
│   │   ├── letters/              # Recommendation letter templates (v1, v2)
│   │   ├── essays/               # Personal essay templates (v1, v2)
│   │   └── variables/            # CSV lookup tables (names, traits, hometowns, etc.)
│   ├── src/
│   │   ├── generate_letters.py   # Latin-square letter generation (120 letters)
│   │   ├── generate_essays.py    # Latin-square essay generation (60 essays)
│   │   ├── generate_submissions.py  # Paired essay+letter submissions (60)
│   │   ├── generate_name_only.py # Name-only-varied letters
│   │   ├── generate_drive_essays.py # Name-swap real essays
│   │   ├── score_letters.py      # Score any JSON via OpenRouter (parallel)
│   │   ├── visualize_results.py  # Radar charts per model
│   │   ├── analyze_all.py        # Cross-model comparison (radar, heatmap, box, effect sizes)
│   │   ├── analyze_drive_essays.py  # Analysis for real-essay pipeline
│   │   ├── analyze_grok_debias.py   # Grok debiased-prompt deep dive
│   │   └── compare_prompts.py    # Original-vs-simple prompt comparison
│   ├── data/                     # Generated materials + score JSONs
│   └── results/                  # PNG charts and visualizations
│
└── data/                         # Shared / scraped data
    ├── generated_essays/
    ├── generated_letters/
    ├── generated_submissions/
    ├── drive_essays.json
    └── scores*.json
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm   # needed by pdf_to_json.py
```

Create `credentials.json` from the example for `openrouter_client.py`:

```bash
cp credentials.example.json credentials.json
```

Set your OpenRouter key for the scoring pipeline:

```bash
echo 'OPENROUTER_API_KEY=your-key-here' > aaron_letters/.env
```

## Running the pipeline

### 1. Generate application materials

```bash
cd aaron_letters

# Synthetic letters (Latin square, 120 letters)
python src/generate_letters.py

# Synthetic essays (Latin square, 60 essays)
python src/generate_essays.py

# Combined essay+letter submissions (60)
python src/generate_submissions.py

# Name-only variation letters
python src/generate_name_only.py

# Name-swap real essays (requires data/drive_essays.json)
python src/generate_drive_essays.py
```

### 2. Score with LLMs

```bash
# score_letters.py <input_file> <output_file> [prompt_variant]
# prompt_variant: "original" (default), "debias", "metadata", or "simple"

python src/score_letters.py generated_letters/letters.json scores.json original
python src/score_letters.py generated_letters/letters.json scores_debias.json debias
python src/score_letters.py generated_letters/letters.json scores_metadata.json metadata
```

### 3. Analyze and visualize

```bash
# Full cross-model analysis
python src/analyze_all.py

# Drive essay analysis
python src/analyze_drive_essays.py

# Compare rubric vs simple prompt
python src/compare_prompts.py
```

Charts are saved to `aaron_letters/results/`.

## Scraping real essays

```bash
# Scrape OpenEssays listings and download essays
python openessays_scraper.py --type BACHELORS --download-essays --max-essays 50

# Fetch original source URLs (Medium, Google Drive, etc.)
python openessays_scraper.py \
  --listing-file data/raw/openessays.org/index_type=BACHELORS.html \
  --download-originals --json-output data/bachelors.json

# Convert Google Drive PDFs to structured JSON
python pdf_to_json.py --metadata data/bachelors.json --output data/drive_essays.json

# Post-processing: add name placeholders, ethnicity, and gender
python add_swappable_text.py
python add_likely_ethnicity.py
python assign_likely_gender.py
```

## Key output

- **Radar charts**: Subcategory scores (grammar, tone, academic readiness, life context) by race, split by gender, per model and prompt variant
- **Heatmaps**: Mean scores across race x gender x prompt
- **Box plots**: Score distributions with individual data points
- **Effect size heatmaps**: Cohen's d for racial and gender gaps across all models and prompt conditions
- **Prompt comparison charts**: Side-by-side rubric vs. simple scoring bias
