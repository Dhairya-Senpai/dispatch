"""
send_email Lambda
-----------------
POST /campaigns/{campaignId}/send

Validates the campaign, sanitizes HTML, queues email jobs onto SQS
for async processing by process_queue.
"""
import os
import json
import uuid
import logging

import sys
sys.path.insert(0, "/opt/python")  # Lambda layer path
from utils import success, error, verify_api_key, sanitize_html, validate_email, get_dynamodb, get_sqs, utc_now

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CAMPAIGNS_TABLE = os.environ.get("CAMPAIGNS_TABLE", "dispatch-campaigns")
CONTACTS_TABLE  = os.environ.get("CONTACTS_TABLE",  "dispatch-contacts")
EMAIL_QUEUE_URL = os.environ.get("EMAIL_QUEUE_URL",  "")


def handler(event: dict, context) -> dict:
    # Auth
    if not verify_api_key(event):
        return error("Unauthorized", 401)

    # Parse body
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error("Invalid JSON body")

    campaign_id = (event.get("pathParameters") or {}).get("campaignId")
    if not campaign_id:
        return error("Missing campaignId")

    # Fetch campaign
    db = get_dynamodb()
    campaigns_table = db.Table(CAMPAIGNS_TABLE)
    response = campaigns_table.get_item(Key={"campaignId": campaign_id})
    campaign = response.get("Item")
    if not campaign:
        return error("Campaign not found", 404)

    if campaign.get("status") not in ("draft", "scheduled"):
        return error(f"Campaign cannot be sent from status: {campaign['status']}")

    # Sanitize HTML content
    raw_html = campaign.get("htmlContent", "")
    safe_html = sanitize_html(raw_html)

    # Fetch contacts for this list
    contacts_table = db.Table(CONTACTS_TABLE)
    list_id = campaign.get("listId")
    contacts = _get_contacts_for_list(contacts_table, list_id)

    if not contacts:
        return error("No contacts found for this campaign's list")

    # Enqueue one SQS message per contact
    sqs = get_sqs()
    queued = 0
    failed = 0

    for contact in contacts:
        email = contact.get("email", "")
        if not validate_email(email):
            failed += 1
            continue

        message = {
            "jobId":      str(uuid.uuid4()),
            "campaignId": campaign_id,
            "to":         email,
            "subject":    campaign.get("subject", ""),
            "htmlContent": safe_html,
            "fromAddress": campaign.get("fromAddress", os.environ.get("DEFAULT_FROM_EMAIL", "")),
            "contactId":  contact.get("contactId", ""),
        }

        try:
            sqs.send_message(
                QueueUrl=EMAIL_QUEUE_URL,
                MessageBody=json.dumps(message),
                MessageGroupId=campaign_id,  # FIFO queue grouping
            )
            queued += 1
        except Exception as e:
            logger.error(f"Failed to queue email for {email}: {e}")
            failed += 1

    # Update campaign status
    campaigns_table.update_item(
        Key={"campaignId": campaign_id},
        UpdateExpression="SET #s = :s, sentAt = :t, queuedCount = :q",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "sending", ":t": utc_now(), ":q": queued},
    )

    logger.info(f"Campaign {campaign_id}: queued={queued}, failed={failed}")
    return success({"campaignId": campaign_id, "queued": queued, "failed": failed})


def _get_contacts_for_list(table, list_id: str) -> list:
    """Fetch all contacts belonging to a list. Uses GSI on listId."""
    if not list_id:
        return []
    try:
        response = table.query(
            IndexName="listId-index",
            KeyConditionExpression="listId = :lid",
            ExpressionAttributeValues={":lid": list_id},
        )
        return response.get("Items", [])
    except Exception as e:
        logger.error(f"Failed to fetch contacts for list {list_id}: {e}")
        return []
