"""
ai_service.py — Hugging Face Inference API integration.

Responsibilities (service layer — no FastAPI imports):
  1. Convert an uploaded image's raw bytes into a base64 string (with compression).
  2. Build a strict system prompt with knowledge-base context and strict routing categories.
  3. Call the HuggingFace Inference API using InferenceClient (Dynamic Model Selection).
  4. Robustly extract a valid JSON object from the LLM's raw text output.
  5. Return a typed AIResult to the caller.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import io
from PIL import Image
from dataclasses import dataclass
from typing import Optional

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (DYNAMIC MODELS)
# ---------------------------------------------------------------------------

# Fast model for standard text tickets
_HF_TEXT_MODEL = "Qwen/Qwen2.5-7B-Instruct"

# Vision model (capable of reading images) for screenshot tickets
_HF_VISION_MODEL = "AumCoreAI/HF-BLIP2-Image-Reader"

# Environment — NODE_ENV is the primary deployment identifier per project spec.
_NODE_ENV = os.getenv("NODE_ENV", "development")
_IS_PRODUCTION = _NODE_ENV == "production"

# HF error body text that indicates the looping-content guard fired.
_LOOP_DETECTION_PHRASE = "looping content"


def _get_api_key() -> str:
    """Read the HuggingFace API key from the environment (loaded by main.py)."""
    key = os.getenv("HUGGINGFACE_API_KEY", "")
    if not key or key.startswith("hf_your_token"):
        raise EnvironmentError(
            "HUGGINGFACE_API_KEY is not set. "
            "Add it to backend/.env and restart the server."
        )
    return key


# ---------------------------------------------------------------------------
# Typed result & custom exception
# ---------------------------------------------------------------------------

@dataclass
class AIResult:
    """Structured output from the LLM, always valid regardless of parse path."""
    resolved: bool
    response_or_routing_tags: str
    raw_output: str          # preserved for debugging / logging
    used_fallback: bool = False  # True when keyword routing was used instead of LLM


class LLMLoopError(RuntimeError):
    """Raised when HF's loop-detection guard fires. Caller should use fallback."""


# ---------------------------------------------------------------------------
# Image → base64 helper
# ---------------------------------------------------------------------------

def image_bytes_to_base64(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """
    Resize image to prevent 413 Payload Too Large errors,
    then encode as a base64 JPEG data-URI.
    """
    try:
        # Open the image from bytes
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB (removes alpha channels/transparency which JPEG doesn't support)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize the image so the longest edge is max 800 pixels
        img.thumbnail((800, 800))

        # Save to a new byte buffer as a compressed JPEG
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        compressed_bytes = buffer.getvalue()

        # Encode the much smaller image to base64
        encoded = base64.b64encode(compressed_bytes).decode("utf-8")
        
        logger.info(f"Image compressed from {len(image_bytes)} bytes to {len(compressed_bytes)} bytes")
        return f"data:image/jpeg;base64,{encoded}"
        
    except Exception as e:
        logger.error(f"Failed to compress image: {e}")
        # Fallback to the original uncompressed method if compression fails
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"


# ---------------------------------------------------------------------------
# Prompt builder (STRICT ROUTER + CONVERSATIONAL CHATBOT)
# ---------------------------------------------------------------------------

def _build_prompt(user_message: str, kb_context: str) -> str:
    """
    Build the prompt text. Forces a conversational response if resolved,
    or a strict single-word department string if escalated.
    """
    return (
        f"You are a helpful, conversational 1st-line IT support chatbot.\n"
        f"Knowledge Base: {kb_context}\n\n"
        f"User Issue: {user_message}\n\n"
        f"INSTRUCTIONS:\n"
        f"Step 1: Check if the Knowledge Base contains the answer to the User Issue.\n"
        f"Step 2: If YES, write a polite, full-sentence explanation answering the user's question directly.\n"
        f"Step 3: If NO, you must route the ticket to one of these exact departments: [auth, database, deployment, frontend, api, monitoring].\n\n"
        f"RESPOND STRICTLY IN JSON FORMAT:\n"
        f"- If you found the answer: {{\"resolved\": true, \"response_or_routing_tags\": \"<write your friendly, full-sentence chatbot answer here>\"}}\n"
        f"- If routing is needed: {{\"resolved\": false, \"response_or_routing_tags\": \"<department_name>\"}}\n\n"
        f"Output nothing except the JSON."
    )


def _build_kb_context(knowledge_base: list[dict], max_articles: int = 4) -> str:
    """Produce a short, inline KB context string."""
    lines: list[str] = []
    for article in knowledge_base[:max_articles]:
        content = article["content"].replace("**", "")
        lines.append(f"[{article['topic']}] {content}")
    return " | ".join(lines)


# ---------------------------------------------------------------------------
# Robust JSON extraction
# ---------------------------------------------------------------------------

_JSON_BLOCK_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


def _extract_json(raw_text: str) -> dict:
    """Extract a JSON object from raw LLM output. Never raises."""
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        candidate = json.loads(text)
        if isinstance(candidate, dict) and "resolved" in candidate:
            return candidate
    except json.JSONDecodeError:
        pass

    matches = _JSON_BLOCK_RE.findall(text)
    for match in matches:
        try:
            candidate = json.loads(match)
            if isinstance(candidate, dict) and "resolved" in candidate:
                logger.debug("JSON extracted via regex from LLM output")
                return candidate
        except json.JSONDecodeError:
            continue

    logger.warning(
        "Could not extract valid JSON from LLM output. Raw text: %s",
        text[:300],
    )
    # Default fallback to "api" if extraction completely fails
    return {"resolved": False, "response_or_routing_tags": "api"}


# ---------------------------------------------------------------------------
# HuggingFace API call 
# ---------------------------------------------------------------------------

def _call_huggingface(
    api_key: str,
    prompt_text: str,
    image_data_uri: Optional[str],
    target_model: str,  # <-- NEW PARAMETER
) -> str:
    """
    Calls the HuggingFace Inference API using the official Python client.
    """
    client = InferenceClient(token=api_key)

    if image_data_uri:
        content = [
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": image_data_uri}}
        ]
    else:
        content = prompt_text

    messages = [{"role": "user", "content": content}]

    try:
        response = client.chat_completion(
            model=target_model, # <-- DYNAMICALLY INJECTED MODEL
            messages=messages,
            max_tokens=200,
            temperature=0.1,
            seed=42
        )
        return response.choices[0].message.content

    except HfHubHTTPError as e:
        err_msg = str(e).lower()
        if _LOOP_DETECTION_PHRASE in err_msg:
            logger.warning("HuggingFace loop-detection guard fired. Falling back.")
            raise LLMLoopError(err_msg)
        raise e


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def call_llm(
    user_message: str,
    knowledge_base: list[dict],
    image_bytes: Optional[bytes] = None,
    image_mime_type: str = "image/png",
) -> AIResult:
    """Main entry point for the chat router."""
    api_key = _get_api_key()

    has_image = bool(image_bytes)
    
    # --- DYNAMIC MODEL SELECTION ---
    target_model = _HF_VISION_MODEL if has_image else _HF_TEXT_MODEL

    if has_image:
        logger.info(
            "Image attached — %d bytes (%.1f KB), MIME: %s",
            len(image_bytes),
            len(image_bytes) / 1024,
            image_mime_type,
        )

    kb_context = _build_kb_context(knowledge_base)
    prompt_text = _build_prompt(user_message, kb_context)

    image_data_uri: Optional[str] = None
    if has_image:
        image_data_uri = image_bytes_to_base64(image_bytes, image_mime_type)

    logger.info(
        "Calling HuggingFace API | model=%s | env=%s | has_image=%s",
        target_model, # <-- LOGGING WHICH MODEL WE ARE USING
        _NODE_ENV,
        has_image,
    )

    try:
        raw_output = _call_huggingface(
            api_key=api_key,
            prompt_text=prompt_text,
            image_data_uri=image_data_uri,
            target_model=target_model, # <-- PASSING THE CHOSEN MODEL
        )
    except LLMLoopError:
        logger.info("LLM loop fallback: using keyword-based KB search.")
        return _keyword_fallback(user_message, knowledge_base)

    logger.debug("Raw LLM output: %s", raw_output[:500])

    parsed = _extract_json(raw_output)
    resolved: bool = bool(parsed.get("resolved", False))
    payload: str = str(parsed.get("response_or_routing_tags", "")).strip()

    return AIResult(
        resolved=resolved,
        response_or_routing_tags=payload,
        raw_output=raw_output,
    )


# ---------------------------------------------------------------------------
# Keyword-based fallback
# ---------------------------------------------------------------------------

def _keyword_fallback(user_message: str, knowledge_base: list[dict]) -> AIResult:
    """Fallback to keyword matching against the KB."""
    lower = user_message.lower()
    best_match: Optional[str] = None
    best_score = 0

    for article in knowledge_base:
        score = sum(1 for kw in article["keywords"] if kw in lower)
        if score > best_score:
            best_score = score
            best_match = article["content"]

    if best_match and best_score > 0:
        return AIResult(
            resolved=True,
            response_or_routing_tags=(
                f"{best_match}\n\n"
                "*(Answer provided by knowledge base — AI model temporarily unavailable.)*"
            ),
            raw_output="[keyword-fallback]",
            used_fallback=True,
        )

    return AIResult(
        resolved=False,
        response_or_routing_tags="api",
        raw_output="[keyword-fallback-no-match]",
        used_fallback=True,
    )