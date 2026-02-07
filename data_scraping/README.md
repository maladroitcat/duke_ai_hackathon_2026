# OpenRouter Script Starter

This folder holds a tiny Python helper that shows how to call the [OpenRouter](https://openrouter.ai/) chat completions API. It also includes a credentials template so you can keep your API key out of the source tree.

## Setup

1. Create a virtual environment and install the single dependency:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy the sample credentials file and add your real API key:
   ```bash
   cp credentials.example.json credentials.json
   $EDITOR credentials.json
   ```
   - `api_key` is your OpenRouter key
   - `model` can be any model that OpenRouter exposes (e.g. `openrouter/auto`)
   - `extra_headers` are optional, but OpenRouter asks for `HTTP-Referer` and `X-Title`

## Sending a prompt

```bash
python openrouter_client.py --prompt "Hello from OpenRouter!"
```

Optional flags:
- `--system` adds a system instruction
- `--model` overrides the model from the credentials file
- `--credentials` points to a different JSON file if you want to keep multiple keys

On success, the assistant reply is printed to stdout. Any HTTP or network issues are reported on stderr.

## Scraping OpenEssays

`openessays_scraper.py` downloads one or more `openessays.org` pages into `data/raw/` while honoring `robots.txt`. Listing pages include `originalUrl` fields that usually point to Medium/Twitter/etc., so the scraper can optionally fetch those external articles as well. Whenever HTML is fetched (either from OpenEssays or the original source) the script extracts readable text (BeautifulSoup for HTML, pdfminer for PDFs, python-docx for DOCX, GitHub raw for Markdown, Jina proxy for X/Twitter) and writes one JSON record per essay so you don’t have to open the raw HTML.

```bash
# Single URL
python openessays_scraper.py --url https://openessays.org/some-page

# Multiple paths listed in a file
python openessays_scraper.py --urls-file urls.txt --delay 2.0

# Grab the BACHELORS listing and then fetch every essay page it references
python openessays_scraper.py --type BACHELORS --download-essays --max-essays 20

# Reuse an already-downloaded listing HTML file to pull the essays it references
python openessays_scraper.py \
  --listing-file data/raw/openessays.org/index_type=BACHELORS.html \
  --download-essays

# Listing entries often just embed `originalUrl`s; fetch those directly as a fallback
python openessays_scraper.py \
  --listing-file data/raw/openessays.org/index_type=BACHELORS.html \
  --download-originals --max-essays 50 \
  --json-output data/bachelors.json

# Convert the saved Google Drive PDFs into structured JSON with inferred metadata
python pdf_to_json.py --metadata data/bachelors.json --output data/drive_essays.json
```

Useful flags:
- `--output-dir data/custom` saves HTML somewhere else
- `--user-agent "MyResearchBot/1.0"` sets a custom user agent header
- `--type BACHELORS` (repeatable) crawls listing pages without hand-writing URLs
- `--listing-file path/to/file.html` rehydrates slugs from an existing listing download
- `--download-essays --max-essays 100` grabs each `/essay/<slug>` page referenced by the listings
- `--download-originals` also downloads the external `originalUrl` (Medium/Twitter/etc.). This is useful when `/essay/<slug>` is missing or returns 404.
- `--json-output data/essays.json` controls where parsed text + metadata records are written (defaults to `data/essays.json`).
- `--pdf-dir data/pdfs` keeps a copy of any raw PDFs pulled from Google Drive so you can review the originals later.
- `--skip-robots` disables the robots check (only use if you have explicit permission)

Domain-specific download handling currently includes:
- Google Drive & Docs: converts share links to direct download/export, stores the raw PDF under `data/pdfs/`, and runs pdfminer / python-docx on the binary output.
- GitHub & Gist: rewrites blob URLs to their raw equivalents so you get pure Markdown/plaintext rather than site chrome.
- X.com/Twitter: proxies through `https://r.jina.ai/` to bypass the JS wall and capture the full tweet text.

### PDF post-processing

`pdf_to_json.py` iterates over the PDFs in `data/pdfs/`, extracts plain text with pdfminer, merges in metadata from `data/bachelors.json`, heuristically guesses the applicant name from the slug, and infers gender if the text clearly uses gendered pronouns. The output is a compact JSON file for downstream analysis.

> Note: `pdf_to_json.py` uses spaCy for PERSON detection. Install the model once via `python -m spacy download en_core_web_sm` before running the script.
