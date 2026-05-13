"""
process_queue Lambda
--------------------
Triggered by SQS. Processes each email job and sends via SES.
Records delivery status back to DynamoDB.
"""
import os
import json
import logging

import sys
sys.path.insert(0, "/opt/python")
from utils import get_ses, get_dynamodb, utc_now, validate_url

logger = logging.getLogger()
logger.setLevel(logging.INFO)

JOBS_TABLE       = os.environ.get("JOBS_TABLE",       "dispatch-jobs")
TRACKING_BASE_URL = os.environ.get("TRACKING_BASE_URL", "")


def handler(event: dict, context) -> dict:
    db   = get_dynamodb()
    ses  = get_ses()
    jobs = db.Table(JOBS_TABLE)

    batch_failures = []

    for record in event.get("Records", []):
        job_id = None
        try:
            body = json.loads(record["body"])
            job_id = body["jobId"]

            # Inject tracking pixel and wrap links
            html = _inject_tracking(body["htmlContent"], body["campaignId"], body["contactId"])

            ses.send_email(
                Source=body["fromAddress"],
                Destination={"ToAddresses": [body["to"]]},
                Message={
                    "Subject": {"Data": body["subject"], "Charset": "UTF-8"},
                    "Body":    {"Html": {"Data": html, "Charset": "UTF-8"}},
                },
                Tags=[
                    {"Name": "campaignId", "Value": body["campaignId"]},
                    {"Name": "jobId",      "Value": job_id},
                ],
            )

            # Record success
            jobs.put_item(Item={
                "jobId":      job_id,
                "campaignId": body["campaignId"],
                "contactId":  body["contactId"],
                "email":      body["to"],
                "status":     "sent",
                "sentAt":     utc_now(),
            })

            logger.info(f"Sent jobId={job_id} to={body['to']}")

        except Exception as e:
            logger.error(f"Failed jobId={job_id}: {e}")
            # Return failed message IDs so SQS retries them
            batch_failures.append({"itemIdentifier": record["messageId"]})

            if job_id:
                try:
                    jobs.put_item(Item={
                        "jobId":     job_id,
                        "status":    "failed",
                        "error":     str(e),
                        "failedAt":  utc_now(),
                    })
                except Exception:
                    pass

    return {"batchItemFailures": batch_failures}


def _inject_tracking(html: str, campaign_id: str, contact_id: str) -> str:
    """Append a 1x1 tracking pixel and rewrite links for click tracking."""
    if not TRACKING_BASE_URL or not validate_url(TRACKING_BASE_URL):
        return html

    pixel_url = f"{TRACKING_BASE_URL}/track/open?c={campaign_id}&u={contact_id}"
    pixel = f'<img src="{pixel_url}" width="1" height="1" alt="" style="display:none;" />'

    # Close body tag injection
    if "</body>" in html:
        html = html.replace("</body>", f"{pixel}</body>")
    else:
        html += pixel

    return html
