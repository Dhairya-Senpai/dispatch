"""
campaign_ai Lambda
------------------
POST /campaigns/generate

Uses Google Gemini to generate email campaign subject lines and HTML body
based on a user prompt and campaign metadata.
"""
import os
import json
import logging

import sys
sys.path.insert(0, "/opt/python")
from utils import success, error, verify_api_key, sanitize_html

import google.generativeai as genai

logger = logging.getLogger()
logger.setLevel(logging.INFO)

GEMINI_MODEL = "gemini-1.5-flash"


def handler(event: dict, context) -> dict:
    if not verify_api_key(event):
        return error("Unauthorized", 401)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return error("Gemini API key not configured", 500)

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error("Invalid JSON body")

    prompt      = body.get("prompt", "").strip()
    brand_name  = body.get("brandName", "")
    tone        = body.get("tone", "professional")  # professional | friendly | urgent
    campaign_type = body.get("campaignType", "newsletter")

    if not prompt:
        return error("prompt is required")

    if len(prompt) > 1000:
        return error("prompt must be under 1000 characters")

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)

        system_prompt = f"""You are an expert email marketing copywriter.
Generate email campaign content based on the user's request.
Brand: {brand_name or 'the sender'}
Tone: {tone}
Campaign type: {campaign_type}

Respond ONLY with valid JSON in this exact format:
{{
  "subject": "Email subject line here",
  "previewText": "Short preview text (50 chars max)",
  "htmlContent": "<p>Full HTML email body here</p>",
  "plainText": "Plain text version of the email"
}}

Rules:
- Subject line: compelling, under 60 characters
- HTML: clean, minimal, no external CSS, use inline styles only
- Include a clear call-to-action
- No placeholder text like [YOUR NAME]"""

        response = model.generate_content(f"{system_prompt}\n\nUser request: {prompt}")
        raw = response.text.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        generated = json.loads(raw)

        # Sanitize the generated HTML before returning
        if "htmlContent" in generated:
            generated["htmlContent"] = sanitize_html(generated["htmlContent"])

        return success(generated)

    except json.JSONDecodeError:
        logger.error("Gemini returned non-JSON response")
        return error("Failed to parse AI response", 500)
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return error("AI generation failed", 500)
