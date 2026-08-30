"""Sanitized logging helpers — no PII, no secrets, no raw questions when PII is possible."""
from __future__ import annotations

import logging


def safe_log(logger: logging.Logger, message: str, extra: dict | None = None) -> None:
    payload = {"msg": message}
    if extra:
        # only whitelisted, non-PII keys
        allowed = {"question_hash", "intent", "source_id", "scheme", "topic", "count", "file_name"}
        payload.update({k: v for k, v in extra.items() if k in allowed})
    logger.info("%s %s", payload.get("msg"), {k: v for k, v in payload.items() if k != "msg"})
