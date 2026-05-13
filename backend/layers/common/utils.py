"""
Common utilities shared across Lambda functions.
"""
import os
import json
import logging
import re
from typing import Any
from datetime import datetime, timezone

import bleach
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# ── Response helpers ──────────────────────────────────────────────────────────

def success(body: Any, status: int = 200) -> dict:
    return {
        "statusCode": status,
        "headers": cors_headers(),
        "body": json.dumps(body, default=str),
    }


def error(message: str, status: int = 400) -> dict:
    return {
        "statusCode": status,
        "headers": cors_headers(),
        "body": json.dumps({"error": message}),
    }


def cors_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
    }


# ── Security ──────────────────────────────────────────────────────────────────

ALLOWED_TAGS = [
    "a", "b", "br", "em", "h1", "h2", "h3", "h4", "h5", "h6",
    "i", "img", "li", "ol", "p", "span", "strong", "table",
    "tbody", "td", "th", "thead", "tr", "ul",
]

ALLOWED_ATTRS = {
    "a": ["href", "title", "target"],
    "img": ["src", "alt", "width", "height"],
    "*": ["style", "class"],
}

URL_PATTERN = re.compile(
    r'^https?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$',
    re.IGNORECASE,
)


def sanitize_html(html: str) -> str:
    """Strip disallowed tags and attributes from HTML content."""
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


def validate_url(url: str) -> bool:
    """Return True if url is a valid http/https URL."""
    return bool(URL_PATTERN.match(url))


def validate_email(email: str) -> bool:
    pattern = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
    return bool(pattern.match(email))


# ── Auth ──────────────────────────────────────────────────────────────────────

def verify_api_key(event: dict) -> bool:
    """Validate API key from request headers."""
    expected = os.environ.get("API_KEY")
    if not expected:
        logger.warning("API_KEY environment variable not set")
        return False
    provided = (event.get("headers") or {}).get("x-api-key", "")
    return provided == expected


# ── AWS clients (lazy, module-level singletons) ───────────────────────────────

_dynamodb = None
_sqs = None
_ses = None


def get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _dynamodb


def get_sqs():
    global _sqs
    if _sqs is None:
        _sqs = boto3.client("sqs", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _sqs


def get_ses():
    global _ses
    if _ses is None:
        _ses = boto3.client("ses", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _ses


# ── Timestamps ────────────────────────────────────────────────────────────────

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
