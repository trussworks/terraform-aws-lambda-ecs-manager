import pytest as _pytest

import functions.pkg.manager as manager


class TestLambdaHandler:
    @_pytest.mark.parametrize(
        ("test_input", "expected"),
        [
            (
                {"body": "mybody"},
                {
                    "msg": "Required field(s) not found",
                    "data": "'['command']' field(s) not optional. "
                    "Found: ['body'].  Required: ['command', 'body']",
                },
            ),
            (
                {"command": "mycommand"},
                {
                    "msg": "Required field(s) not found",
                    "data": "'['body']' field(s) not optional. "
                    "Found: ['command'].  Required: ['command', 'body']",
                },
            ),
            (
                {},
                {
                    "msg": "Required field(s) not found",
                    "data": "'['command', 'body']' field(s) not optional. "
                    "Found: [].  Required: ['command', 'body']",
                },
            ),
            (
                {"wrongkey1": "", "wrongkey2": ""},
                {
                    "msg": "Required field(s) not found",
                    "data": "'['command', 'body']' field(s) not optional. "
                    "Found: ['wrongkey1', 'wrongkey2'].  "
                    "Required: ['command', 'body']",
                },
            ),
        ],
    )
    def test_required_fields(self, test_input, expected, mocker):
        mocker.patch.dict(manager.__DISPATCH__, {})
        result = manager.lambda_handler(test_input)

        assert result == expected

    @_pytest.mark.parametrize(
        ("test_input", "expected"),
        [
            (
                {"command": "runtask", "body": "mybody"},
                {
                    "msg": "response received",
                    "data": {
                        "duration": "0 ms",
                        "response": {
                            "ResponseMetadata": {"HTTPStatusCode": "200"},
                            "foo": "bar",
                            "request_payload": {
                                "body": "mybody",
                                "command": "runtask",
                            },
                        },
                    },
                },
            )
        ],
    )
    def test_runtask_dispatch(
        self, test_input, expected, mocker, result_with_body
    ):
        mocker.patch("time.time", return_value=100)
        mock_runtask = mocker.patch.object(
            manager, "_runtask", return_value=result_with_body
        )
        mocker.patch.dict(manager.__DISPATCH__, {"runtask": mock_runtask})

        result = manager.lambda_handler(event=test_input, context=None)

        mock_runtask.assert_called_once_with(test_input["body"])
        assert result == expected
