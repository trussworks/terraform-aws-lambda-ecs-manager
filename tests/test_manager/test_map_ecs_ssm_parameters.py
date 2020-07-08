import functions.manager as manager


class TestMapECS:
    def test_returns_Boto3Result(
        self, mock_ssm_client, mock_invoke, boto3result
    ):
        r = manager._map_ecs_ssm_parameters(
            mock_ssm_client, [{"some_key": "some_value"}]
        )
        assert isinstance(r, boto3result)

    def test_list_tags_called_for_each_resource(
        self, mock_ssm_client, mock_invoke, mocker
    ):
        manager._map_ecs_ssm_parameters(
            mock_ssm_client, [{"Name": num} for num in range(0, 10)]
        )
        assert mock_invoke.call_count == 10
        assert mock_invoke.call_args_list == [
            mocker.call(
                mock_ssm_client.list_tags_for_resource,
                ResourceType="Parameter",
                ResourceId=num,
            )
            for num in range(0, 10)
        ]

    def test_map(
        self, mock_ssm_client, mock_invoke, fake_ssm_stored_parameters
    ):
        for f_param in fake_ssm_stored_parameters:
            f_tags = f_param.get("fake_tags", [])
            mock_invoke.return_value.body = {"TagList": f_tags}

            result = manager._map_ecs_ssm_parameters(
                mock_ssm_client, [f_param]
            )

            result_map = result.body.get("map", [None])
            if result_map:
                assert result_map[0].get("name") == f_tags[0].get("Value")
            else:
                assert result_map == []
