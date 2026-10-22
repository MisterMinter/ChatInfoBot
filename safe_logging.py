"""Redact credentials before logs, alerts, or telemetry leave the process."""
import logging
import os
import re

_TELEGRAM_URL = re.compile(r"(api\.telegram\.org/(?:file/)?bot)[0-9]+(?::|%3[aA])[A-Za-z0-9_-]+", re.I)
_TELEGRAM_TOKEN = re.compile(r"[0-9]{6,}(?::|%3[aA])[A-Za-z0-9_-]{20,}")
_DISCORD_WEBHOOK = re.compile(r"(discord(?:app)?\.com/api/webhooks/)[^\s/]+/[^\s\"'<>]+", re.I)
_SECRET_NAME = re.compile(r"TOKEN|SECRET|PASSWORD|API_KEY|WEBHOOK|SENTRY_DSN", re.I)


def redact_text(value):
    text = str(value)
    for name, secret in os.environ.items():
        if _SECRET_NAME.search(name) and len(secret) >= 8:
            text = text.replace(secret, "[REDACTED]")
    text = _TELEGRAM_URL.sub(r"\1[REDACTED]", text)
    text = _TELEGRAM_TOKEN.sub("[REDACTED]", text)
    return _DISCORD_WEBHOOK.sub(r"\1[REDACTED]", text)


def redact_data(value):
    if isinstance(value, dict):
        return {key: redact_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_data(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_sentry_event(event, hint=None):
    return redact_data(event)


class RedactingFormatter(logging.Formatter):
    def format(self, record):
        # Format first so interpolation and exception tracebacks are redacted too.
        return redact_text(super().format(record))


def configure_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        root.addHandler(logging.StreamHandler())
    formatter = RedactingFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    for handler in root.handlers:
        handler.setFormatter(formatter)
    # Routine HTTP request URLs contain the Telegram bot token.
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
