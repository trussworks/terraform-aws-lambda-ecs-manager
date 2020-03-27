import pytest as _pytest


class TestBoto3Result:
    def test_Boto3Result_with_body(self, result_with_body):
        assert result_with_body.status == "200"
        assert result_with_body.body == {
            "status": "200",
            "response": {
                "ResponseMetadata": {"HTTPStatusCode": "200"},
                "foo": "bar",
            },
        }
        assert result_with_body.exc is None
        assert result_with_body.error == {}

    def test_Boto3Result_with_exception(
        self, result_with_exception, test_exception
    ):
        assert result_with_exception.status is None
        assert result_with_exception.body == {
            "status": None,
            "response": {},
        }
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
    pass
