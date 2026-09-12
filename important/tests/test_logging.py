import io
import json
import logging
from src.app.logging import JsonFormatter, ScrapingRunScope, get_logger


def test_json_formatter_and_scraping_run_scope() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())

    test_logger = logging.getLogger("test_structured_logger")
    test_logger.handlers.clear()
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.INFO)
    test_logger.propagate = False

    # 1. Log outside of scope
    test_logger.info("Message without scraping scope")
    line1 = json.loads(stream.getvalue().strip().split("\n")[-1])
    assert line1["message"] == "Message without scraping scope"
    assert "scraping_run_id" not in line1
    assert "level" in line1
    assert "timestamp" in line1

    # 2. Log inside ScrapingRunScope
    with ScrapingRunScope(scraping_run_id=42, company_id=7, target_id=10):
        test_logger.info("Inside run scope", extra={"event": "FETCH_COMPLETED"})
        line2 = json.loads(stream.getvalue().strip().split("\n")[-1])
        assert line2["message"] == "Inside run scope"
        assert line2["scraping_run_id"] == 42
        assert line2["company_id"] == 7
        assert line2["target_id"] == 10
        assert line2["event"] == "FETCH_COMPLETED"

    # 3. Log after scope exits - context should be cleared
    test_logger.info("After run scope exited")
    line3 = json.loads(stream.getvalue().strip().split("\n")[-1])
    assert line3["message"] == "After run scope exited"
    assert "scraping_run_id" not in line3
