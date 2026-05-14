"""
DLQ Lambda handler — design_doc §6 / implementation_plan.md problem-4 fix.

Triggered by: SQS Dead Letter Queue event (after llm_queue or pdf_queue exhausts retries).

Responsibilities:
  1. Parse the failed SQS message to extract diagnosis_id + error context.
  2. Write a JobError record to the job_errors table.
  3. Publish an SNS alert so on-call is notified immediately.

Deployed as an independent Lambda function (lambda_dlq Terraform module)
so DLQ handling scales independently from the main workers.
"""
import json
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django  # noqa: E402
django.setup()

import boto3  # noqa: E402
from django.conf import settings  # noqa: E402

from apps.diagnosis.models import JobError  # noqa: E402


def handler(event, context):
    """
    AWS Lambda entry point for DLQ messages.

    Each record in the event is a message that failed all retries in the
    main LLM or PDF queue.
    """
    sns_client = boto3.client("sns", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    sns_topic_arn = os.environ.get("SNS_ALERT_TOPIC_ARN", "")

    for record in event.get("Records", []):
        sqs_message_id = record.get("messageId", "")
        body_raw = record.get("body", "{}")

        try:
            body = json.loads(body_raw)
        except json.JSONDecodeError:
            body = {}

        diagnosis_id = body.get("diagnosis_id")
        error_type = body.get("error_type", "TASK_EXHAUSTED_RETRIES")
        error_message = body.get("error_message", body_raw)
        retry_count = int(record.get("attributes", {}).get("ApproximateReceiveCount", 0))

        # Persist failure record to DB (best-effort — don't let a DB failure
        # prevent the SNS alert from going out).
        if diagnosis_id:
            try:
                JobError.objects.create(
                    diagnosis_id=diagnosis_id,
                    error_type=error_type,
                    error_message=error_message,
                    sqs_message_id=sqs_message_id,
                    retry_count=retry_count,
                )
            except Exception as db_exc:
                print(f"[dlq_handler] DB write failed: {db_exc}")

        # Publish SNS alert.
        if sns_topic_arn:
            alert_subject = f"[DLQ ALERT] diagnosis_id={diagnosis_id} — {error_type}"
            alert_message = (
                f"A task has been moved to the Dead Letter Queue after exhausting retries.\n\n"
                f"diagnosis_id : {diagnosis_id}\n"
                f"error_type   : {error_type}\n"
                f"retry_count  : {retry_count}\n"
                f"sqs_message  : {sqs_message_id}\n\n"
                f"error_message:\n{error_message}"
            )
            try:
                sns_client.publish(
                    TopicArn=sns_topic_arn,
                    Subject=alert_subject,
                    Message=alert_message,
                )
            except Exception as sns_exc:
                print(f"[dlq_handler] SNS publish failed: {sns_exc}")

    return {"status": "processed", "count": len(event.get("Records", []))}
