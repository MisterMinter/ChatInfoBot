import io
import logging
import os
import unittest
from unittest.mock import patch

from safe_logging import RedactingFormatter, configure_logging, redact_sentry_event

TOKEN = "123456789:" + "A" * 35
URL = "https://api.telegram.org/bot" + TOKEN + "/getUpdates"


class RedactionTests(unittest.TestCase):
    def render(self, message, *args, exc_info=None):
        record = logging.LogRecord("httpx", logging.WARNING, __file__, 1, message, args, exc_info)
        return RedactingFormatter("%(message)s").format(record)

    def test_request_arguments_and_encoded_urls_are_redacted(self):
        for url in (URL, URL.replace(":", "%3A", 1).replace("https%3A", "https:"), URL.replace(TOKEN, TOKEN.replace(":", "%3A"))):
            text = self.render("Request failed: %s", url)
            self.assertNotIn(TOKEN, text)
            self.assertNotIn("A" * 35, text)
            self.assertIn("getUpdates", text)

    def test_exception_traceback_is_redacted(self):
        try:
            raise RuntimeError(URL)
        except RuntimeError:
            import sys
            text = self.render("Request failed", exc_info=sys.exc_info())
        self.assertIn("RuntimeError", text)
        self.assertNotIn(TOKEN, text)

    def test_configured_secrets_and_nested_telemetry_are_redacted(self):
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "private-token-for-test"}):
            data = redact_sentry_event({"exception": [{"value": URL}], "request": {"secret": "private-token-for-test"}})
        self.assertNotIn(TOKEN, str(data))
        self.assertNotIn("private-token-for-test", str(data))

    def test_webhook_credentials_are_redacted(self):
        text = self.render("Failed: https://discord.com/api/webhooks/123/private-webhook-value")
        self.assertNotIn("private-webhook-value", text)

    def test_http_request_info_logs_are_suppressed(self):
        root = logging.getLogger()
        old_handlers, old_level = root.handlers[:], root.level
        logger = logging.getLogger("httpx")
        old_http_level = logger.level
        stream = io.StringIO()
        root.handlers = [logging.StreamHandler(stream)]
        try:
            configure_logging()
            logger.info("HTTP Request: %s", URL)
            logger.warning("Request failed: %s", URL)
            self.assertNotIn("HTTP Request:", stream.getvalue())
            self.assertNotIn(TOKEN, stream.getvalue())
            self.assertIn("Request failed:", stream.getvalue())
        finally:
            root.handlers, root.level = old_handlers, old_level
            logger.setLevel(old_http_level)


if __name__ == "__main__":
    unittest.main()
