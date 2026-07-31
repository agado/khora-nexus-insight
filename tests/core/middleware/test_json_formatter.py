import json
import logging

from src.core.middleware import JSONFormatter


def test_json_formatter_basic():
    formatter = JSONFormatter(datefmt="%Y-%m-%dT%H:%M:%S")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello",
        args=(),
        exc_info=None,
    )
    output = json.loads(formatter.format(record))
    assert output["level"] == "INFO"
    assert output["message"] == "hello"
    assert "time" in output


def test_json_formatter_extra_fields():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="request",
        args=(),
        exc_info=None,
    )
    record.method = "GET"
    record.path = "/health"
    record.status = 200
    record.request_id = "abc-123"
    output = json.loads(formatter.format(record))
    assert output["message"] == "request"
    assert output["method"] == "GET"
    assert output["path"] == "/health"
    assert output["status"] == 200
    assert output["request_id"] == "abc-123"


def test_json_formatter_excludes_reserved_attrs():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="test %s",
        args=("value",),
        exc_info=None,
    )
    output = json.loads(formatter.format(record))
    assert output["message"] == "test value"
    assert "args" not in output
