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
