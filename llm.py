import hashlib
import json
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()
_client = anthropic.Anthropic()

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)


def generate(messages, model=DEFAULT_MODEL, system=None,
             max_tokens=1024, sample_id=0):
    """Call Claude, with a disk cache so identical requests are never paid for twice."""
    key_src = json.dumps(
        {"model": model, "messages": messages, "system": system,
         "sample_id": sample_id},
        sort_keys=True,
    )
    key = hashlib.sha256(key_src.encode()).hexdigest()
    path = CACHE_DIR / f"{key}.json"

    if path.exists():
        return json.loads(path.read_text())["text"]

    kwargs = dict(model=model, max_tokens=max_tokens, messages=messages)
    if system:
        kwargs["system"] = system
    resp = _client.messages.create(**kwargs)
    text = resp.content[0].text

    path.write_text(json.dumps({
        "text": text,
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
    }))
    return text


def extract_code(text):
    """Pull the code out of a ```python ... ``` block; fall back to the raw text."""
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.DOTALL)
    return max(blocks, key=len) if blocks else text