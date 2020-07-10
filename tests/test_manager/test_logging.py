import json
import logging

import pytest as _pytest

import functions.manager as manager


def _logging_message(msg="", data=None):
    return json.dumps({"message": msg, "data": data}, default=str)


def test_logger_level():
    assert manager.LOGGER.getEffectiveLevel() == logging.INFO


@_pytest.mark.parametrize(
    ("levelname", "levelno", "expected_log_count"),
    [
        ("debug", logging.DEBUG, 0),
        ("info", logging.INFO, 1),
        ("warning", logging.WARNING, 1),
        ("critical", logging.CRITICAL, 1),
    ],
)
def test_log_output_per_level(caplog, levelname, levelno, expected_log_count):
    msg = "logging message"
    data = "logging data"
    expected = _logging_message(msg=msg, data=data)

    manager.log(msg=msg, data=data, level=levelname)

    assert len(caplog.records) == expected_log_count
    if expected_log_count:
        assert caplog.records[0].message == expected
        assert caplog.records[0].levelno == levelno
