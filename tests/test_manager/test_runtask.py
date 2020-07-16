import logging

import pytest as _pytest

import functions.manager as manager
from functions.manager import Boto3Result as Boto3Result


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
        [{"service_id": "some_service"}, {"cluster_id": "some_cluster"}],
    )
    def test_required_keys_present(mock_invoke, body, caplog):
        result = manager._runtask(body)

        assert isinstance(result, Boto3Result)
        assert isinstance(result.exc, KeyError)
        assert result.error is not None
        assert result.body == {}

        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.CRITICAL

    def test_entrypoint_requires_container_id(mock_invoke):
        result = manager._runtask(
            {
                "entrypoint": "someentrypoint",
                "cluster_id": "somecluster",
                "service_id": "someservice",
            }
        )
        assert isinstance(result, Boto3Result)
        assert isinstance(result.exc, KeyError)
        assert result.error is not None
        assert result.body == {}
