"""Vision-language model calls with on-disk caching (results/cache) so re-runs are free.

Model and key come from .env / environment: ANTHROPIC_API_KEY, VLM_MODEL (default claude-sonnet-5-5).
"""
from __future__ import annotations
import base64, hashlib, json, os
from pathlib import Path
from dotenv import load_dotenv
from .paths import ROOT, CACHE

load_dotenv(ROOT / ".env")
MODEL = os.environ.get("VLM_MODEL", "claude-sonnet-5-5")
_client = None


def have_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


def ask(image_path: Path, prompt: str, max_tokens: int = 4000) -> str:
    """One image + prompt -> reply text. On current models the reasoning counts towards max_tokens as well
    as the answer, so the ceiling is generous (billing is per token produced, not per ceiling). A reply that
    did not finish normally (cut off, refused) is never cached or scored: the run stops instead."""
    data = Path(image_path).read_bytes()
    key = hashlib.sha256(MODEL.encode() + data + prompt.encode()).hexdigest()
    CACHE.mkdir(parents=True, exist_ok=True)
    cpath = CACHE / f"{key}.json"
    if cpath.exists():
        return json.loads(cpath.read_text())["text"]
    msg = _get_client().messages.create(
        model=MODEL, max_tokens=max_tokens,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(data).decode()}},
            {"type": "text", "text": prompt},
        ]}],
    )
    if msg.stop_reason != "end_turn":
        raise RuntimeError(f"{MODEL} did not finish its reply for {image_path} "
                           f"(stop_reason={msg.stop_reason}); nothing was cached for this call")
    text = "".join(b.text for b in msg.content if b.type == "text")
    cpath.write_text(json.dumps({"model": MODEL, "image": str(image_path), "prompt": prompt, "text": text,
                                 "stop_reason": msg.stop_reason,
                                 "usage": {"input_tokens": msg.usage.input_tokens,
                                           "output_tokens": msg.usage.output_tokens}}))
    return text


def extract_json(text: str):
    """Pull the first JSON object/array out of a model reply."""
    import re
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    body = m.group(1) if m else text
    start = min([i for i in (body.find("{"), body.find("[")) if i >= 0], default=-1)
    if start < 0:
        return None
    for end in range(len(body), start, -1):
        try:
            return json.loads(body[start:end])
        except json.JSONDecodeError:
            continue
    return None
