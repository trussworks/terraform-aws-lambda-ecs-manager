import itertools

import pytest as _pytest

import functions.manager as manager
from functions.manager import Boto3Result as Boto3Result

required_keys = ["container_id", "service_id", "cluster_id"]
required_keys_combinations = itertools.combinations(required_keys, 2)


class TestValidations:
    def test_entrypoint_type(mock_invoke):
        result = manager._runtask({"entrypoint": [1, 2, 3]})

        assert isinstance(result.exc, TypeError)
        assert result.error is not None
        assert result.body == {}

    @_pytest.mark.parametrize(
        ("body"),
        [
            {combo[0]: "foo", combo[1]: "bar"}
            for combo in required_keys_combinations
        ],
    )
    def test_required_keys_present(mock_invoke, body):
        return
        result = manager._runtask(body)

        assert isinstance(result, Boto3Result)
        assert result.exc == KeyError(manager._missing_required_keys())
