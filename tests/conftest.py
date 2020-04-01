import pytest as _pytest

from functions.runtask import Boto3Error, Boto3InputError, Boto3Result


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
def test_exception_raiser():
    def foo():
        raise Boto3Error

    return foo


@_pytest.fixture
def botoresult():
    return Boto3Result


@_pytest.fixture
def result_with_body():
    return Boto3Result(
        response={"ResponseMetadata": {"HTTPStatusCode": "200"}, "foo": "bar"}
    )


@_pytest.fixture
def result_with_exception(test_exception):
    try:
        raise test_exception
    except test_exception as te:
        return Boto3Result(response=None, exc=te)
