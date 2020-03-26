import pytest as _pytest

import functions.aws as aws
from functions.aws import Boto3InputError


class TestException(Exception):
    pass


@_pytest.fixture
def generic_mock(mocker):
    return mocker.MagicMock


@_pytest.fixture
def result_with_body(mocker):
    return aws.Boto3Result(
        response={"ResponseMetadata": {"HTTPStatusCode": "200"}, "foo": "bar"}
    )


@_pytest.fixture
def result_with_exception(mocker):
    try:
        raise TestException
    except TestException as te:
        return aws.Boto3Result(response=None, exc=te)


class TestBoto3Result:
    def test_Boto3Result_with_body(self, result_with_body):
        assert result_with_body.status == "200"
        assert result_with_body.body == {
            "ResponseMetadata": {"HTTPStatusCode": "200"},
            "foo": "bar",
        }
        assert result_with_body.exc is None
        assert result_with_body.error == {}

    def test_Boto3Result_with_exception(self, result_with_exception):
        assert result_with_exception.status is None
        assert result_with_exception.body is None
        assert isinstance(result_with_exception.exc, TestException)
        assert isinstance(result_with_exception.error, dict)
        assert all(
            key in result_with_exception.error
            for key in ("title", "message", "traceback")
        )

    def test_Boto3Result_with_neither(self):
        with _pytest.raises(Boto3InputError):
            aws.Boto3Result()


class TestInvoke:
    pass
