#!/usr/bin/env python3
"""
Simple helper to call the OpenRouter chat completions endpoint.

Usage example:
    python openrouter_client.py --prompt "Hello, who are you?"
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, List

import requests

DEFAULT_CREDENTIALS = pathlib.Path("credentials.json")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def load_credentials(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Credentials file '{path}' not found. Copy credentials.example.json "
            "to credentials.json and add your API key."
        )

    with path.open() as handle:
        data = json.load(handle)

    api_key = data.get("api_key")
    if not api_key or not isinstance(api_key, str):
        raise ValueError("Missing 'api_key' in credentials file")

    model = data.get("model", "openrouter/auto")
    if not isinstance(model, str):
        raise ValueError("'model' must be a string")

    extra_headers = data.get("extra_headers", {})
    if extra_headers and not isinstance(extra_headers, dict):
        raise ValueError("'extra_headers' must be a JSON object if provided")

    return {
        "api_key": api_key,
        "model": model,
        "extra_headers": extra_headers or {},
    }


def create_payload(model: str, prompt: str, system: str | None) -> Dict[str, Any]:
    messages: List[Dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return {"model": model, "messages": messages}


def call_openrouter(api_key: str, payload: Dict[str, Any], extra_headers: Dict[str, str] | None = None) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://example.com",
        "X-Title": "OpenRouter Script",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a prompt through OpenRouter")
    parser.add_argument(
        "--prompt",
        required=True,
        help="The user prompt to send to the model",
    )
    parser.add_argument(
        "--system",
        help="Optional system instruction (default: none)",
    )
    parser.add_argument(
        "--credentials",
        type=pathlib.Path,
        default=DEFAULT_CREDENTIALS,
        help="Path to credentials JSON (default: credentials.json)",
    )
    parser.add_argument(
        "--model",
        help="Override the model specified in credentials",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    creds = load_credentials(args.credentials)
    if args.model:
        creds["model"] = args.model

    payload = create_payload(creds["model"], args.prompt, args.system)

    try:
        data = call_openrouter(creds["api_key"], payload, creds.get("extra_headers"))
    except requests.HTTPError as exc:
        print(f"OpenRouter request failed: {exc.response.text}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 1

    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    content = message.get("content")
    if content:
        print(content)
    else:
        print(json.dumps(data, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
