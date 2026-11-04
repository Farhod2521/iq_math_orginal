"""
Turli AI provayderlar bilan ishlash uchun yagona klient. Sozlamalar .env dan olinadi:

    AI_URL=https://api.anthropic.com          # yoki https://api.x.ai/v1, https://api.deepseek.com ...
    AI_KEY=sk-...
    AI_MODEL=claude-opus-5-5                  # grok-4, deepseek-chat ...
    AI_FORMAT=anthropic                       # anthropic | openai (Grok, DeepSeek, OpenAI — openai formatida)

Ixtiyoriy: AI_TIMEOUT (soniya, standart 180), AI_MAX_TOKENS (standart 8000).
"""
import json
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()


class AIError(Exception):
    pass


def ai_settings():
    return {
        "url": (os.getenv("AI_URL") or "").strip().rstrip("/"),
        "key": (os.getenv("AI_KEY") or "").strip(),
        "model": (os.getenv("AI_MODEL") or "").strip(),
        "format": (os.getenv("AI_FORMAT") or "anthropic").strip().lower(),
        "timeout": int(os.getenv("AI_TIMEOUT") or 180),
        "max_tokens": int(os.getenv("AI_MAX_TOKENS") or 8000),
    }


def is_configured():
    s = ai_settings()
    return bool(s["url"] and s["key"] and s["model"])


def _endpoint(base, suffix):
    # AI_URL to'liq manzil (…/v1/messages) yoki faqat asosiy qism (…/v1) bo'lishi mumkin
    if base.endswith(suffix):
        return base
    if suffix == "/v1/messages" and base.endswith("/v1"):
        return base + "/messages"
    return base + suffix


def _anthropic_content(prompt, images):
    if not images:
        return prompt
    blocks = []
    for image in images:
        if image.get("url"):
            blocks.append({"type": "image", "source": {"type": "url", "url": image["url"]}})
        else:
            blocks.append({
                "type": "image",
                "source": {"type": "base64", "media_type": image["media_type"], "data": image["data"]},
            })
    blocks.append({"type": "text", "text": prompt})
    return blocks


def _openai_content(prompt, images):
    if not images:
        return prompt
    blocks = [{"type": "text", "text": prompt}]
    for image in images:
        url = image.get("url") or f"data:{image['media_type']};base64,{image['data']}"
        blocks.append({"type": "image_url", "image_url": {"url": url}})
    return blocks


def _call_anthropic(s, system, prompt, images):
    resp = requests.post(
        _endpoint(s["url"], "/v1/messages"),
        headers={
            "x-api-key": s["key"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": s["model"],
            "max_tokens": s["max_tokens"],
            "system": system,
            "messages": [{"role": "user", "content": _anthropic_content(prompt, images)}],
        },
        timeout=s["timeout"],
    )
    if resp.status_code >= 400:
        raise AIError(f"AI xatosi ({resp.status_code}): {resp.text[:300]}")
    body = resp.json()
    return "".join(block.get("text", "") for block in body.get("content", []) if block.get("type") == "text")


def _call_openai(s, system, prompt, images):
    resp = requests.post(
        _endpoint(s["url"], "/chat/completions"),
        headers={"Authorization": f"Bearer {s['key']}", "Content-Type": "application/json"},
        json={
            "model": s["model"],
            "max_tokens": s["max_tokens"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": _openai_content(prompt, images)},
            ],
        },
        timeout=s["timeout"],
    )
    if resp.status_code >= 400:
        raise AIError(f"AI xatosi ({resp.status_code}): {resp.text[:300]}")
    body = resp.json()
    try:
        return body["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise AIError("AI javobi kutilgan formatda emas")


def complete(system, prompt, images=None):
    """
    So'rov sozlangan provayderga yuboriladi, javob matni qaytadi.
    images — rasmlar ro'yxati: {"media_type": "image/png", "data": "<base64>"} yoki {"url": "https://..."}.
    """
    s = ai_settings()
    if not is_configured():
        raise AIError(".env da AI_URL, AI_KEY, AI_MODEL sozlanmagan")
    try:
        if s["format"] == "anthropic":
            return _call_anthropic(s, system, prompt, images)
        return _call_openai(s, system, prompt, images)
    except requests.Timeout:
        raise AIError("AI javob berishga ulgurmadi (timeout)")
    except requests.RequestException as exc:
        raise AIError(f"AI bilan bog'lanib bo'lmadi: {exc}")


def parse_json(text):
    """Model javobidan JSON obyektni ajratib oladi (```json bloklari va izohlarga chidamli)."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    try:
        return json.loads(cleaned)
    except ValueError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise AIError("AI javobidan JSON topilmadi")
        try:
            return json.loads(cleaned[start:end + 1])
        except ValueError:
            raise AIError("AI javobidagi JSON buzilgan")
