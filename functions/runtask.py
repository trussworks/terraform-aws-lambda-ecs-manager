"""Lambda function for running ECS tasks."""
import json
import logging
import os
import sys
import time
import traceback
import types
from typing import Any, Dict, Optional

import boto3

LOGGER = logging.getLogger()
LOGGER_LEVEL = logging.DEBUG
LOGGER.setLevel(LOGGER_LEVEL)


def log(msg: str = "", data: Any = None, level: str = "debug") -> None:
    """Log a structured message to the console."""
    j = json.dumps({"message": msg, "data": data})
    getattr(LOGGER, level)(f"{j}")


class Boto3Error(Exception):
    """Generic Boto3Error exception."""

    pass


class Boto3InputError(Boto3Error, AttributeError):
    """AttributeError variant for Boto3Error."""

    pass


class Boto3Result:
    """Result from a boto3 module call."""

    def __init__(
        self,
        response: Optional[Dict[str, Any]] = None,
        exc: Optional[Exception] = None,
    ):
        """Instance constructor.

        If an exception is passed, provide a dictionary representation of the
        traceback. Otherwise, return the response object.

        Arguments:
            response: dict with a response message.
                    Optional if exc is passed
            exc: Exception raised in a boto3 client method.
                    Optional if response is passed

        Raises:
            Boto3InputError if neither optional argument is provided
        """
        if not isinstance(response, dict) and not isinstance(exc, Exception):
            raise Boto3InputError("At least one argument is required")

        if response is not None:
            self.status = response.get("ResponseMetadata", {}).get(
                "HTTPStatusCode"
            )
        else:
            self.status = None

        self.body: Dict[str, Any] = response or {}
        self.exc: Optional[Exception] = exc
        self.error: Dict[str, Any] = self._get_error_msg()

    def _get_error_msg(self) -> Dict[str, Any]:
        """Return the response stacktrace, if any."""
        if self.exc is None:
            return {}

        tb = traceback.TracebackException.from_exception(
            self.exc, capture_locals=True
        )
        return {
            "title": type(self.exc).__name__,
            "message": str(self.exc),
            "traceback": list(tb.format()),
        }


def invoke(boto3_function: types.FunctionType, **kwargs: Any) -> Boto3Result:
    """Call a function and return the response as a Boto3Result."""
    try:
        r = boto3_function(**kwargs)
    except Exception as exc:
        return Boto3Result(exc=exc)
    else:
        return Boto3Result(response=r or {})


def _generate_container_definition(
    taskdef: Dict[str, Any], container_name: str, command: str
) -> Dict[str, Any]:
    """Create a definition to run the given command on the given container.

    Arguments:
        taskdef:
            task definition to use in the container definition
        container_name:
            name of the container to use as a template for the new
            container definition
        command:
            new command for the container definition

    Raises:
        KeyError:
            if the container_name is not found in the taskdef
    """
    container_definiton: Dict[str, Any]
    for container_definition in taskdef["containerDefinitions"]:
        if container_definition["name"] == container_name:
            break
    else:
        raise KeyError(f"Definition for container {container_name} not found.")

    container_definition["logConfiguration"]["options"][
        "awslogs-stream-prefix"
    ] = "lambda"
    container_definition.update(
        command=command,
        portMappings=[],  # nothing should connect to this container
    )
    return container_definition  # type: ignore


def _runtask(command: str) -> Boto3Result:
    """Runs an ECS service optionally updating the task command."""
    _environment = os.environ["ENVIRONMENT"]
    _cluster = os.environ["ECS_CLUSTER"]
    _service = os.environ["ECS_SERVICE"]
    taskdef_family = f"{_service}-lambda-{_environment}"

    ecs = boto3.client("ecs")

    r = invoke(
        ecs.describe_services, **{"cluster": _cluster, "services": [_service]}
    )
    if r.exc:
        return Boto3Result(exc=r.exc)
    netconf = r.body["services"][0]["networkConfiguration"]
    svc_taskdef_arn = r.body["services"][0]["taskDefinition"]

    if command:
        _container_name = os.environ["ECS_CONTAINER"]
        r = invoke(
            ecs.describe_task_definition, **{"taskDefinition": svc_taskdef_arn}
        )
        if r.exc:
            return Boto3Result(exc=r.exc)
        service_taskdef = r.body["taskDefinition"]

        # create and register a custom task definition by modifying the
        # existing service
        r = invoke(
            ecs.register_task_definition,
            **{
                "family": taskdef_family,
                "containerDefinitions": [
                    _generate_container_definition(
                        service_taskdef, _container_name, command
                    )
                ],
                "executionRoleArn": service_taskdef["executionRoleArn"],
                "taskRoleArn": service_taskdef["taskRoleArn"],
                "networkMode": service_taskdef["networkMode"],
                "cpu": service_taskdef["cpu"],
                "memory": service_taskdef["memory"],
                "requiresCompatibilities": service_taskdef[
                    "requiresCompatibilities"
                ],
            },
        )
        if r.exc:
            return Boto3Result(exc=r.exc)
        target_taskdef_arn = r.body["taskDefinition"]["taskDefinitionArn"]
        log(msg="Created task definition", data=target_taskdef_arn)
    else:
        target_taskdef_arn = svc_taskdef_arn

    # run the task
    r = invoke(
        ecs.run_task,
        **{
            "cluster": _cluster,
            "taskDefinition": target_taskdef_arn,
            "launchType": "FARGATE",
            "networkConfiguration": netconf,
            "startedBy": "lambda",
        },
    )
    new_task_arn = r.body["tasks"][0]["taskArn"]
    if r.exc:
        return Boto3Result(exc=r.exc)
    log(msg="Running task", data=new_task_arn)

    # wait for the task to finish
    r = _task_wait(ecs=ecs, cluster=_cluster, task_arn=new_task_arn)
    if r.exc:
        return Boto3Result(exc=r.exc)
    log(msg="Finished waiting for task execution", data=new_task_arn)

    # inspect task result
    r = invoke(
        ecs.describe_tasks, **{"cluster": _cluster, "tasks": [new_task_arn]}
    )
    if r.exc:
        return Boto3Result(exc=r.exc)

    if r.body["failures"]:
        return Boto3Result(
            exc=Exception(
                f"ecs.describeTask call returned errors on {new_task_arn}",
                r.body["failures"],
            )
        )

    task_description = r.body["tasks"][0]
    container_description = task_description["containers"][0]
    task_status = {
        key: value
        for key, value in task_description.items()
        if key in ("stopCode", "stoppedReason", "startedBy", "taskArn")
    }
    task_status.update({"exitCode": container_description["exitCode"]})

    return Boto3Result(
        response={
            "taskArn": new_task_arn,
            "taskDefinitionArn": target_taskdef_arn,
            "taskStatus": task_status,
        }
    )


def _task_wait(
    ecs: boto3.client,
    cluster: str,
    task_arn: str,
    delay: int = 6,
    attempts: int = 20,
) -> Boto3Result:
    waiter = ecs.get_waiter("tasks_stopped")
    r = invoke(
        waiter.wait,
        **{
            "cluster": cluster,
            "tasks": [task_arn],
            "WaiterConfig": {"Delay": delay, "MaxAttempts": attempts},
        },
    )
    if r.exc:
        return Boto3Result(exc=r.exc)
    else:
        return Boto3Result(response={})


def lambda_handler(event: Dict[str, str], context: Any = None) -> None:
    """Define a Lambda function entry-point.

    Takes an dictionary event, processes it, and logs a response message.

    Args:
        event: A dictionary with an optional command.
        context: This is ignored.

    Returns:
        None
    """
    start_t = time.time()
    log(msg="event received", data=event)
    command = event.get("command") or ""
    response = {"request_payload": command}

    result = _runtask(command)
    response.update(result.body)

    duration = "{} ms".format(round(1000 * (time.time() - start_t), 2))
    log(
        msg="response received",
        data={"response": response, "duration": duration},
    )
    sys.exit(result.body.get("taskStatus", {}).get("exitCode", 1))


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s %(message)s", level=LOGGER_LEVEL)
    started_by = os.environ["USER"]
    event = json.loads(sys.argv[1])

    lambda_handler(event)
