# AI Approach & Hallucination Prevention

This document outlines how the meeting analysis is built, how we query Gemini, and how we prevent it from hallucinating or fabricating details.

## Model Selection
We went with **Gemini 3.5 Flash** (using the `google-generativeai` Python SDK). 
* It's very fast, meaning we can run analyses synchronously without making the user wait long.
* The model follows complex instructions well, particularly when forced to output structured JSON.
* It supports native async calls (`generate_content_async`), allowing FastAPI's event loop to continue serving other requests.

## Prompt Design & Structure
Instead of asking Gemini to write a summary and extract action items in free-form text, we supply a strict system prompt that demands a structured JSON response.

### 1. The Strict Grounding Rules
We prefix our prompt with explicit, non-negotiable rules:
* You must ONLY use facts directly stated in the transcript.
* Do NOT invent tasks, outcomes, decisions, or attendees.
* Every single point extracted (summary sentence, action item, decision, suggestion) MUST reference at least one timestamp from the transcript.
* Only reference timestamps that are actually in the transcript.
* If there's no evidence for something, leave it out.

### 2. Output Schema
We force the model to return JSON matching this exact structure:
```json
{
  "summary": [{"text": "...", "citations": [{"timestamp": "HH:MM"}]}],
  "actionItems": [{"task": "...", "assignee": "...", "citations": [...]}],
  "decisions": [{"decision": "...", "citations": [...]}],
  "followUps": [{"suggestion": "...", "citations": [...]}]
}
```
## How Citation Grounding Works
To verify every insight, the model returns a `citations` list for each item, linking it back to the exact time of the discussion.

For example, if the transcript has:
`[00:15] Chloe: I will setup the database environment tomorrow.`

The AI output will yield:
```json
{
  "task": "Setup the database environment",
  "assignee": "Chloe",
  "citations": [{"timestamp": "00:15"}]
}
```

## 3 Layers of Hallucination Defense

Even with a good prompt, LLMs can still hallucinate timestamps. We built a three-layer defense to keep the data clean:

### Layer 1: Prompt Restraints
We instruct the model directly that hallucinating timestamps will result in validation failure.

### Layer 2: Post-Processing Validation (Backend)
When Gemini returns the JSON payload, our backend runs a validator. It maps all the actual timestamps present in the original transcript. It then checks every single citation in the AI's response:
* If a citation uses a timestamp that doesn't exist in the transcript, it is removed.
* If an AI-generated item loses all its citations, we discard the item entirely.

### Layer 3: Markdown Fence Cleaning
Gemini sometimes wraps JSON responses in markdown blocks (e.g., ` ```json ... ``` `). Before parsing, the backend cleans off these blocks to prevent parsing errors.


## Current Limitations & Notes

1. **Timestamp Formats**: The matching logic expects standard formats (`MM:SS` or `HH:MM:SS`). If a transcript uses irregular formats like `12-30` or `12:3`, citation matching might fail.
2. **Short Transcripts**: If a transcript has only one or two short sentences, the AI might return an empty list of action items or decisions. This is expected behavior.
3. **Assignee Names vs. Emails**: The AI extracts assignee names as mentioned in the text (e.g., "Chloe" or "Tom"). Our reminder service sends emails, so it looks for email addresses. If the AI assignee is just a first name, the reminder service logs a warning and skips sending the email until a user updates it to a valid email address.
4. **Token Capacity & Rate Limits**: Extremely long transcripts could run into context limits or prompt delays. Also, the free tier of the Gemini API is limited to 60 requests/minute.
