"""
S3 Adapter — design_doc §2 "PDF report storage, Pre-signed URL"

Upload strategy:
  - If settings.AWS_S3_BUCKET_NAME is set → real S3 (boto3)
  - Otherwise → local filesystem under media/ (development fallback)

Pre-signed URL expiry: 15 minutes (900 seconds), as per design_doc §4.3.
"""
import os
from pathlib import Path

from django.conf import settings


class S3Adapter:

    PRESIGNED_URL_EXPIRY = 900  # design_doc §4.3 — 15 minutes

    @staticmethod
    def upload(pdf_bytes: bytes, s3_key: str) -> str:
        """
        Upload PDF bytes and return the s3_key (unchanged).
        Real S3: uploads to settings.AWS_S3_BUCKET_NAME.
        Local fallback: writes to BASE_DIR/media/<s3_key>.
        """
        if settings.AWS_S3_BUCKET_NAME:
            import boto3

            s3 = boto3.client(
                "s3",
                region_name=settings.AWS_DEFAULT_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            s3.put_object(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Key=s3_key,
                Body=pdf_bytes,
                ContentType="application/pdf",
            )
        else:
            # Local filesystem fallback — store under project media/ directory
            local_path = Path(settings.BASE_DIR) / "media" / s3_key
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(pdf_bytes)

        return s3_key

    @staticmethod
    def generate_presigned_url(s3_key: str) -> str:
        """
        design_doc §4.3 — 15-minute Pre-signed URL.
        Local fallback: returns a /media/ relative URL (good enough for dev).
        """
        if settings.AWS_S3_BUCKET_NAME:
            import boto3

            s3 = boto3.client(
                "s3",
                region_name=settings.AWS_DEFAULT_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            return s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.AWS_S3_BUCKET_NAME, "Key": s3_key},
                ExpiresIn=S3Adapter.PRESIGNED_URL_EXPIRY,
            )
        else:
            # Dev: return a local media URL the browser can GET directly
            return f"/media/{s3_key}"
