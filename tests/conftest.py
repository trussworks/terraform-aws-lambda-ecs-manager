import json

import pytest as _pytest

import functions.manager as manager
from functions.manager import Boto3Error, Boto3InputError, Boto3Result


@_pytest.fixture
def test_exception():
    class TestException(Exception):
        pass

    return TestException


@_pytest.fixture
def error_exception():
    return Boto3Error


@_pytest.fixture
def inputerror_exception():
    return Boto3InputError


@_pytest.fixture
def boto3result():
    return Boto3Result


@_pytest.fixture
def test_function():
    def foo(string):
        return f"your string was {string}"

    return foo


@_pytest.fixture
def test_exception_raiser(mocker):
    return mocker.Mock(side_effect=Boto3Error("test_error"))


@_pytest.fixture
def result_with_body():
    return Boto3Result(
        response={"ResponseMetadata": {"HTTPStatusCode": "200"}, "foo": "bar"}
    )


@_pytest.fixture
def result_with_exception(test_exception):
    try:
        raise test_exception("Test exception")
    except test_exception as te:
        return Boto3Result(response=None, exc=te)


@_pytest.fixture
def fake_ecs_client(mocker):
    return mocker.MagicMock()


@_pytest.fixture
def mock_ssm_client(mocker):
    return mocker.MagicMock()


@_pytest.fixture
def mock_invoke(mocker, result_with_body):
    return mocker.patch.object(
        manager, "invoke", autospec=True, return_value=result_with_body
    )


@_pytest.fixture
def fake_ssm_stored_parameters():
    with open("tests/data/ssm_parameters_stored.json") as f:
        return json.load(f)


@_pytest.fixture
def fake_taskdef():
    with open("tests/sample_task_definition.json") as f:
        return json.load(f)
