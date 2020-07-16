import itertools
import logging

import pytest as _pytest

import functions.manager as manager
from functions.manager import Boto3Result as Boto3Result

required_keys = ["container_id", "service_id", "cluster_id"]
required_keys_combinations = itertools.combinations(required_keys, 2)


class TestValidations:
    def test_entrypoint_type(mock_invoke, caplog):
        result = manager._runtask({"entrypoint": [1, 2, 3]})

        assert isinstance(result.exc, TypeError)
        assert result.error is not None
        assert result.body == {}

        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.CRITICAL

    @_pytest.mark.parametrize(
        ("body"),
        [
            {combo[0]: "foo", combo[1]: "bar"}
            for combo in required_keys_combinations
        ],
    )
    def test_required_keys_present(mock_invoke, body, caplog):
        result = manager._runtask(body)

        assert isinstance(result, Boto3Result)
        assert isinstance(result.exc, KeyError)
        assert result.error is not None
        assert result.body == {}

        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.CRITICAL
