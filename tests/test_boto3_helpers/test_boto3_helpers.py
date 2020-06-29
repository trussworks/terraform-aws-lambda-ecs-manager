import ast
from http import HTTPStatus

import pytest as _pytest

import functions.manager as manager
from functions.manager import Boto3Error as Boto3Error
from functions.manager import Boto3Result as Boto3Result


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
        assert result_with_exception.error["title"] == "TestException"
        assert result_with_exception.error["message"] == "Test exception"
        assert result_with_exception.error["traceback"][0] == [
            "Traceback (most recent call last):",
            "",
        ]
        assert len(result_with_exception.error["traceback"][0]) > 1

    def test_Boto3Result_with_neither(self, inputerror_exception, boto3result):
        with _pytest.raises(inputerror_exception):
            boto3result()

    def test_Boto3Result_with_http_failure(self):
        response = {
            "ResponseMetadata": {"HTTPStatusCode": "429"},
            "foo": "bar",
        }
        result_with_http_failure = Boto3Result(response=response)
        assert result_with_http_failure.body == response
        assert result_with_http_failure.status == "429"
        assert result_with_http_failure.exc is None
        assert result_with_http_failure.error == {
            "message": {"response": response},
            "title": "HTTP status not OK: 429",
            "traceback": None,
        }

    def test_Boto3Result_with_failures(self):
        """Sometimes the response will simply have a list of 'failures'."""
        response = {"failures": [{"arn": "some_arn", "reason": "MISSING"}]}
        result_with_failures = Boto3Result(response=response)
        assert result_with_failures.body == response
        assert result_with_failures.status != HTTPStatus.OK.value
        assert result_with_failures.exc is None
        assert result_with_failures.error == {
            "message": [{"arn": "some_arn", "reason": "MISSING"}],
            "title": "Response included failures",
            "traceback": None,
        }

    def test_Boto3Result_empty_http_status(self):
        """Make sure we don't print an error if there's no HTTP status code."""
        response = {"ResponseMetadata": {"HTTPStatusCode": None}}
        result = Boto3Result(response=response)
        assert result.error == {}

    def test_Boto3Result_repr(self, result_with_body, result_with_exception):
        r = "{'ResponseMetadata': {'HTTPStatusCode': '200'}, 'foo': 'bar'}"
        assert repr(result_with_body) == r

        result_dict = ast.literal_eval(repr(result_with_exception))
        assert result_dict.get("title") == "TestException"
        assert result_dict.get("message") == "Test exception"
        assert isinstance(result_dict.get("traceback"), list)


class TestInvoke:
    def test_invoke_body(self, mocker):
        mock_function = mocker.Mock(return_value={"somedict": "return_value"})
        params = {"foo": "foo_arg", "bar": "bar_arg", "baz": "baz_arg"}

        result = manager.invoke(mock_function, **params)

        mock_function.assert_called_once_with(**params)
        assert isinstance(result, Boto3Result)
        assert result.body == {"somedict": "return_value"}
        assert result.exc is None

    def test_invoke_exc(self, test_exception_raiser):
        result = manager.invoke(test_exception_raiser)

        assert isinstance(result, Boto3Result)
        assert result.body == {}
        assert isinstance(result.exc, Boto3Error)


class TestUpdateService:
    def test_update_service(self, mocker, mock_ecs_client, mock_invoke):
        result = manager.update_service(
            ecs_client=mock_ecs_client,
            service_name="some_service_name",
            taskdef_id="some_taskdef_id",
            cluster_id="some_cluster",
        )

        assert isinstance(result, Boto3Result)
        assert isinstance(result.body, dict)
        assert result.exc is None

        mock_invoke.assert_called_once_with(
            mock_ecs_client.update_service,
            **{
                "service": "some_service_name",
                "cluster": "some_cluster",
                "taskDefinition": "some_taskdef_id",
                "forceNewDeployment": False,
            },
        )

    @_pytest.mark.parametrize(
        ("update_service_args", "expected_invoke_args"),
        [
            (
                {
                    "service_name": "some_service_name",
                    "cluster_id": "some_cluster",
                },
                {
                    "cluster": "some_cluster",
                    "forceNewDeployment": False,
                    "service": "some_service_name",
                    "taskDefinition": None,
                },
            )
        ],
    )
    def test_update_service_exc(
        self,
        mocker,
        mock_ecs_client,
        mock_invoke,
        result_with_exception,
        update_service_args,
        expected_invoke_args,
    ):
        mock_invoke.return_value = result_with_exception

        result = manager.update_service(
            ecs_client=mock_ecs_client, **update_service_args
        )

        mock_invoke.assert_called_once_with(
            mock_ecs_client.update_service, **expected_invoke_args
        )
        assert isinstance(result, Boto3Result)
        assert isinstance(result.body, dict)
        assert result.body == {}
        assert isinstance(result.exc, Exception)


class TestRegisterTaskdefinition:
    def test_invoked_with_required_args(
        self, mock_ecs_client, mock_invoke, fake_taskdef
    ):

        manager.register_task_definition(mock_ecs_client, fake_taskdef)

        mock_invoke.assert_called_once_with(
            mock_ecs_client.register_task_definition,
            **{
                "family": fake_taskdef["family"],
                "containerDefinitions": fake_taskdef["containerDefinitions"],
                "executionRoleArn": fake_taskdef["executionRoleArn"],
                "taskRoleArn": fake_taskdef["taskRoleArn"],
                "networkMode": fake_taskdef["networkMode"],
                "cpu": fake_taskdef["cpu"],
                "memory": fake_taskdef["memory"],
                "requiresCompatibilities": fake_taskdef[
                    "requiresCompatibilities"
                ],
            },
        )
