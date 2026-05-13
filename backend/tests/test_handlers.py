"""
Tests for Lambda handlers using moto for AWS mocking.
Run: pytest backend/tests/ -v
"""
import json
import pytest
import boto3
import os
from unittest.mock import patch, MagicMock
from moto import mock_dynamodb, mock_sqs, mock_ses


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("CAMPAIGNS_TABLE", "dispatch-campaigns")
    monkeypatch.setenv("CONTACTS_TABLE", "dispatch-contacts")
    monkeypatch.setenv("JOBS_TABLE", "dispatch-jobs")
    monkeypatch.setenv("EVENTS_TABLE", "dispatch-events")
    monkeypatch.setenv("EMAIL_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789/dispatch-email-queue.fifo")


def make_event(method="GET", path="/", body=None, path_params=None, headers=None):
    return {
        "httpMethod": method,
        "path": path,
        "pathParameters": path_params or {},
        "queryStringParameters": {},
        "headers": headers or {"x-api-key": "test-api-key"},
        "body": json.dumps(body) if body else None,
    }


# ── Utils tests ───────────────────────────────────────────────────────────────

import sys
sys.path.insert(0, "backend/layers/common")
from utils import sanitize_html, validate_url, validate_email


def test_sanitize_html_strips_scripts():
    dirty = '<p>Hello</p><script>alert("xss")</script>'
    clean = sanitize_html(dirty)
    assert "<script>" not in clean
    assert "<p>Hello</p>" in clean


def test_validate_url_accepts_https():
    assert validate_url("https://example.com") is True
    assert validate_url("https://example.com/path?q=1") is True


def test_validate_url_rejects_javascript():
    assert validate_url("javascript:alert(1)") is False
    assert validate_url("ftp://example.com") is False


def test_validate_email():
    assert validate_email("user@example.com") is True
    assert validate_email("invalid-email") is False
    assert validate_email("@nodomain.com") is False


# ── Track event tests ─────────────────────────────────────────────────────────

@mock_dynamodb
def test_track_open_returns_pixel(monkeypatch):
    # Setup DynamoDB tables
    _setup_dynamodb_tables()

    monkeypatch.setenv("TRACKING_BASE_URL", "")
    sys.path.insert(0, "backend/lambdas/track_event")

    # Re-import to pick up env
    import importlib
    import backend.lambdas.track_event.handler as h
    importlib.reload(h)

    event = {
        "path": "/track/open",
        "httpMethod": "GET",
        "queryStringParameters": {"c": "camp-1", "u": "contact-1"},
        "body": None,
        "headers": {},
    }

    response = h.handler(event, None)
    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "image/gif"
    assert response["isBase64Encoded"] is True


@mock_dynamodb
def test_track_click_redirects(monkeypatch):
    _setup_dynamodb_tables()
    monkeypatch.setenv("TRACKING_BASE_URL", "https://dispatch.example.com")

    import importlib
    import backend.lambdas.track_event.handler as h
    importlib.reload(h)

    event = {
        "path": "/track/click",
        "httpMethod": "GET",
        "queryStringParameters": {
            "c": "camp-1",
            "u": "contact-1",
            "url": "https%3A%2F%2Fexample.com",
        },
        "body": None,
        "headers": {},
    }

    response = h.handler(event, None)
    assert response["statusCode"] == 302
    assert response["headers"]["Location"] == "https://example.com"


def test_track_click_rejects_invalid_url(monkeypatch):
    monkeypatch.setenv("TRACKING_BASE_URL", "https://dispatch.example.com")

    import importlib
    import backend.lambdas.track_event.handler as h
    importlib.reload(h)

    event = {
        "path": "/track/click",
        "httpMethod": "GET",
        "queryStringParameters": {"url": "javascript%3Aalert%281%29"},
        "body": None,
        "headers": {},
    }

    response = h.handler(event, None)
    assert response["statusCode"] == 400


# ── Helpers ───────────────────────────────────────────────────────────────────

def _setup_dynamodb_tables():
    client = boto3.client("dynamodb", region_name="us-east-1")
    for table_name in ["dispatch-campaigns", "dispatch-contacts", "dispatch-jobs", "dispatch-events"]:
        try:
            client.create_table(
                TableName=table_name,
                KeySchema=[
                    {"AttributeName": "pk" if table_name == "dispatch-events" else table_name.split("-")[1][:-1] + "Id",
                     "KeyType": "HASH"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "pk" if table_name == "dispatch-events" else table_name.split("-")[1][:-1] + "Id",
                     "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
        except client.exceptions.ResourceInUseException:
            pass
