"""
track_event Lambda
------------------
GET  /track/open   — pixel fire for email opens
GET  /track/click  — link click redirect + record
POST /track/bounce — SES bounce/complaint webhook
"""
import os
import json
import base64
import logging
import urllib.parse

import sys
sys.path.insert(0, "/opt/python")
from utils import get_dynamodb, success, error, utc_now, validate_url

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EVENTS_TABLE    = os.environ.get("EVENTS_TABLE",    "dispatch-events")
CAMPAIGNS_TABLE = os.environ.get("CAMPAIGNS_TABLE", "dispatch-campaigns")

# 1x1 transparent GIF
PIXEL_GIF = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


def handler(event: dict, context) -> dict:
    path   = event.get("path", "")
    method = event.get("httpMethod", "GET")
    params = event.get("queryStringParameters") or {}

    if path.endswith("/track/open"):
        return _handle_open(params)

    if path.endswith("/track/click"):
        return _handle_click(params)

    if path.endswith("/track/bounce") and method == "POST":
        return _handle_bounce(event)

    return error("Not found", 404)


# ── Open tracking ─────────────────────────────────────────────────────────────

def _handle_open(params: dict) -> dict:
    campaign_id = params.get("c", "")
    contact_id  = params.get("u", "")

    if campaign_id and contact_id:
        _record_event("open", campaign_id, contact_id)

    # Return transparent pixel
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type":  "image/gif",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
        "body":            base64.b64encode(PIXEL_GIF).decode(),
        "isBase64Encoded": True,
    }


# ── Click tracking ────────────────────────────────────────────────────────────

def _handle_click(params: dict) -> dict:
    campaign_id  = params.get("c", "")
    contact_id   = params.get("u", "")
    redirect_url = params.get("url", "")

    if not redirect_url:
        return error("Missing redirect url")

    decoded_url = urllib.parse.unquote(redirect_url)

    if not validate_url(decoded_url):
        return error("Invalid redirect URL")

    if campaign_id and contact_id:
        _record_event("click", campaign_id, contact_id, {"url": decoded_url})

    return {
        "statusCode": 302,
        "headers":    {"Location": decoded_url},
        "body":       "",
    }


# ── Bounce / complaint webhook ────────────────────────────────────────────────

def _handle_bounce(event: dict) -> dict:
    try:
        body = json.loads(event.get("body") or "{}")
        # SES sends SNS notification wrapper
        if body.get("Type") == "SubscriptionConfirmation":
            logger.info("SNS subscription confirmation received")
            return success({"status": "ok"})

        message = json.loads(body.get("Message", "{}"))
        notification_type = message.get("notificationType", "")

        if notification_type == "Bounce":
            bounce = message.get("bounce", {})
            for recipient in bounce.get("bouncedRecipients", []):
                _record_event("bounce", "", recipient.get("emailAddress", ""), {
                    "bounceType":    bounce.get("bounceType"),
                    "bounceSubType": bounce.get("bounceSubType"),
                })

        elif notification_type == "Complaint":
            complaint = message.get("complaint", {})
            for recipient in complaint.get("complainedRecipients", []):
                _record_event("complaint", "", recipient.get("emailAddress", ""))

    except Exception as e:
        logger.error(f"Bounce handler error: {e}")
        return error("Failed to process bounce", 500)

    return success({"status": "ok"})


# ── Shared ────────────────────────────────────────────────────────────────────

def _record_event(event_type: str, campaign_id: str, contact_id: str, meta: dict = None):
    try:
        db    = get_dynamodb()
        table = db.Table(EVENTS_TABLE)
        item  = {
            "pk":         f"{campaign_id}#{contact_id}",
            "sk":         f"{event_type}#{utc_now()}",
            "eventType":  event_type,
            "campaignId": campaign_id,
            "contactId":  contact_id,
            "timestamp":  utc_now(),
        }
        if meta:
            item["meta"] = meta

        table.put_item(Item=item)

        # Increment campaign counter
        if campaign_id:
            counter_map = {
                "open":      "openCount",
                "click":     "clickCount",
                "bounce":    "bounceCount",
                "complaint": "complaintCount",
            }
            attr = counter_map.get(event_type)
            if attr:
                db.Table(CAMPAIGNS_TABLE).update_item(
                    Key={"campaignId": campaign_id},
                    UpdateExpression=f"ADD {attr} :one",
                    ExpressionAttributeValues={":one": 1},
                )
    except Exception as e:
        logger.error(f"Failed to record {event_type} event: {e}")
