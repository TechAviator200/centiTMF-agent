import logging
import io

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger("centitmf.s3")

_client = None


def get_s3_client():
    global _client
    if _client is None:
        # endpoint_url=None falls back to AWS S3; set S3_ENDPOINT_URL for MinIO or R2.
        endpoint = settings.S3_ENDPOINT_URL.strip() or None
        _client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.AWS_REGION,
        )
    return _client


def ensure_bucket() -> None:
    """
    Verify the configured bucket is accessible.

    For local MinIO: creates the bucket if it doesn't exist.
    For Cloudflare R2: buckets must be pre-created in the Cloudflare dashboard;
    this function logs a warning rather than crashing if creation fails.
    """
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
        return  # Bucket exists and is accessible
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code not in ("NoSuchBucket", "404", "NoSuchKey"):
            # Access denied or other non-404 error — surface it
            raise

    # Bucket doesn't exist — attempt to create (works for MinIO; may fail on R2)
    try:
        client.create_bucket(Bucket=settings.S3_BUCKET)
        logger.info("Created bucket: %s", settings.S3_BUCKET)
    except ClientError as create_err:
        logger.warning(
            "Could not create bucket '%s': %s. "
            "If using Cloudflare R2, create the bucket in the Cloudflare dashboard first.",
            settings.S3_BUCKET,
            create_err,
        )


def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    client = get_s3_client()
    ensure_bucket()
    client.put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return key


def download_bytes(key: str) -> bytes:
    client = get_s3_client()
    resp = client.get_object(Bucket=settings.S3_BUCKET, Key=key)
    return resp["Body"].read()


def generate_presigned_url(key: str, expires: int = 3600) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=expires,
    )
