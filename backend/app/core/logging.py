import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    # Silence noisy libraries
    for lib in ("httpx", "httpcore", "boto3", "botocore", "urllib3", "s3transfer"):
        logging.getLogger(lib).setLevel(logging.WARNING)


logger = logging.getLogger("centitmf")
