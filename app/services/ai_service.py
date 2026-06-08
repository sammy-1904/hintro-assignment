"""
AI Service — Gemini-powered meeting transcript analysis.

Design principles:
  1. Grounding: the prompt contains the full transcript and instructs the model
     to only reference information explicitly present in it.
  2. Citation validation: after parsing the model output, every citation timestamp
     is checked against the actual transcript timestamps. Hallucinated timestamps
     are silently removed; an item with no valid citations is dropped entirely.
  3. Structured output: we request JSON directly and parse it — no free-form text.
  4. Graceful failure: if Gemini returns malformed JSON, we raise a clear AppError
     rather than crashing the server.
"""

import json
import logging

import google.generativeai as genai

from app.config import settings
from app.utils.errors import AppError

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-3.5-flash")

# ── Prompt ────────────────────────────────────────────────────────────────────

_ANALYSIS_PROMPT = """\
You are an expert meeting analyst. Analyze the transcript below and extract structured insights.

STRICT RULES — violations will disqualify your response:
1. Only include information EXPLICITLY stated in the transcript.
2. Do NOT invent attendees, tasks, decisions, or outcomes.
3. Every item in your response MUST cite at least one timestamp from the transcript.
4. Only cite timestamps that appear in the provided transcript — nothing else.
5. If you cannot ground something in the transcript, omit it entirely.
6. For each item in "actionItems", the "assignee" field MUST be the email address of the person assigned to the task.
   Match the name of the speaker or person mentioned in the transcript to their corresponding email address from the PARTICIPANTS list below.
   If a task is discussed but you cannot resolve the assignee to an email in the PARTICIPANTS list, do NOT invent an email; use their name or omit if completely unresolvable.

PARTICIPANTS:
{participants}

TRANSCRIPT:
{transcript}

Respond with ONLY valid JSON — no markdown fences, no explanation text.
Use this exact structure:
{{
  "summary": [
    {{
      "text": "A concise statement of a key discussion point.",
      "citations": [{{"timestamp": "HH:MM"}}]
    }}
  ],
  "actionItems": [
    {{
      "task": "Specific, actionable task description.",
      "assignee": "Email address from PARTICIPANTS list.",
      "citations": [{{"timestamp": "HH:MM"}}]
    }}
  ],
  "decisions": [
    {{
      "decision": "A clear decision that was made.",
      "citations": [{{"timestamp": "HH:MM"}}]
    }}
  ],
  "followUps": [
    {{
      "suggestion": "A follow-up action or check-in suggestion.",
      "citations": [{{"timestamp": "HH:MM"}}]
    }}
  ]
}}
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_transcript(transcript: list[dict]) -> str:
    return "\n".join(
        f"[{entry['timestamp']}] {entry['speaker']}: {entry['text']}"
        for entry in transcript
    )


def _extract_valid_timestamps(transcript: list[dict]) -> set[str]:
    return {entry["timestamp"] for entry in transcript}


def _clean_citations(citations: list[dict], valid: set[str]) -> list[dict]:
    return [c for c in citations if c.get("timestamp") in valid]


def _validate_and_filter(result: dict, valid_timestamps: set[str]) -> dict:
    """
    Post-processing step: remove any citation referencing a timestamp that does
    not exist in the transcript. Drop any item that ends up with zero citations.
    """
    def clean_list(items: list[dict]) -> list[dict]:
        cleaned = []
        for item in items:
            item["citations"] = _clean_citations(item.get("citations", []), valid_timestamps)
            if item["citations"]:  # only keep items with at least one valid citation
                cleaned.append(item)
        return cleaned

    return {
        "summary": clean_list(result.get("summary", [])),
        "actionItems": clean_list(result.get("actionItems", [])),
        "decisions": clean_list(result.get("decisions", [])),
        "followUps": clean_list(result.get("followUps", [])),
    }


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers that some models include."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last fence lines
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner)
    return text.strip()


# ── Public API ────────────────────────────────────────────────────────────────

async def analyze_transcript(transcript: list[dict], participants: list[str]) -> dict:
    """
    Send transcript to Gemini and return a grounded, citation-validated analysis.

    Returns a dict with keys: summary, actionItems, decisions, followUps.
    Each entry contains citations referencing real transcript timestamps.
    """
    if not transcript:
        raise AppError("EMPTY_TRANSCRIPT", "Cannot analyze an empty transcript.", 422)

    formatted = _format_transcript(transcript)
    valid_timestamps = _extract_valid_timestamps(transcript)
    participants_str = ", ".join(participants)
    prompt = _ANALYSIS_PROMPT.format(participants=participants_str, transcript=formatted)

    logger.info("Sending transcript to Gemini (%d entries)", len(transcript))

    try:
        response = await _model.generate_content_async(prompt)
        raw = _strip_markdown_fences(response.text)
    except Exception as exc:
        logger.exception("Gemini API call failed")
        raise AppError("AI_SERVICE_ERROR", f"AI analysis failed: {str(exc)}", 502) from exc

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Gemini returned non-JSON response: %s", raw[:200])
        raise AppError(
            "AI_PARSE_ERROR",
            "AI returned an unexpected response format. Please try again.",
            502,
        ) from exc

    # Ground the result — strip any hallucinated citations
    validated = _validate_and_filter(result, valid_timestamps)

    total_items = sum(len(v) for v in validated.values())
    logger.info("AI analysis complete — %d grounded items extracted", total_items)

    return validated
