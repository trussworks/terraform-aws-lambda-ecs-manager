import pytest as _pytest

from functions import boto3_helpers


class TestBoto3Result:
    def test_Boto3Result_with_body(self, result_with_body):
        assert result_with_body.status == "200"
        assert result_with_body.body == {
            "ResponseMetadata": {"HTTPStatusCode": "200"},
            "foo": "bar",
        }
        assert result_with_body.exc is None
        assert result_with_body.error == {}

    def test_Boto3Result_with_exception(
        self, result_with_exception, test_exception
    ):
        assert result_with_exception.status is None
        assert result_with_exception.body == {}
        assert isinstance(result_with_exception.exc, test_exception)
        assert isinstance(result_with_exception.error, dict)
        assert all(
            key in result_with_exception.error
            for key in ("title", "message", "traceback")
        )

    def test_Boto3Result_with_neither(self, inputerror_exception, boto3result):
        with _pytest.raises(inputerror_exception):
            boto3result()


class TestInvoke:
    def test_invoke_body(self, mocker):
        mock_function = mocker.Mock(return_value={"somedict": "return_value"})
        params = {"foo": "foo_arg", "bar": "bar_arg", "baz": "baz_arg"}

        result = boto3_helpers.invoke(mock_function, **params)

        mock_function.assert_called_once_with(**params)
        assert isinstance(result, boto3_helpers.Boto3Result)
        assert result.body == {"somedict": "return_value"}
        assert result.exc is None

    def test_invoke_exc(self, test_exception_raiser):
        result = boto3_helpers.invoke(test_exception_raiser)

        assert isinstance(result, boto3_helpers.Boto3Result)
        assert result.body == {}
        assert isinstance(result.exc, boto3_helpers.Boto3Error)
