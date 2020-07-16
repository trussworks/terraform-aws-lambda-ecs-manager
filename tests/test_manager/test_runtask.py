import functions.manager as manager


class TestValidations:
    def test_entrypoint_type(mock_invoke):
        result = manager._runtask({"entrypoint": [1, 2, 3]})

        assert isinstance(result.exc, TypeError)
        assert result.error is not None
        assert result.body == {}
