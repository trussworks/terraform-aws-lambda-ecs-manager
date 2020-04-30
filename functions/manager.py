"""Lambda function for managing ECS tasks and services."""
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Union, cast

import boto3

from .boto3_helpers import Boto3Result, invoke, update_service

LOGGER = logging.getLogger()
LOGGER_LEVEL = logging.DEBUG
LOGGER.setLevel(LOGGER_LEVEL)
STDOUT_HANDLER = logging.StreamHandler(sys.stdout)
STDOUT_HANDLER.setLevel(logging.INFO)
LOGGER.addHandler(STDOUT_HANDLER)


def log(msg: str = "", data: Any = None, level: str = "debug") -> None:
    """Log a structured message to the console."""
    j = json.dumps({"message": msg, "data": data})
    getattr(LOGGER, level)(f"{j}")


# Custom errors
def _missing_required_keys(
    required_keys: List[str], found_keys: List[str]
) -> Dict[str, str]:
    """Computes an error message indicating missing input keys.

    Arguments:
        required_keys: List of required keys.
        found_keys: List of keys that were found in the input.

    Returns:
        A dictionary with a pre-formatted error message.

    Raises:
        TypeError if either argument is not a list.
        ValueError if all the required keys are present.
    """
    if not all(
        [isinstance(required_keys, list), isinstance(found_keys, list)]
    ):
        raise TypeError("argument must be a list type")

    missing_keys = [key for key in required_keys if key not in found_keys]
    if not missing_keys:
        raise ValueError("there were no missing keys")
    return {
        "msg": "Required field(s) not found",
        "data": (
            f"'{missing_keys}' field(s) not optional. "
            f"Found: {found_keys}.  Required: {required_keys}"
        ),
    }


def _generate_container_definition(
    taskdef: Dict[str, Any], container_name: str, entrypoint: str
) -> Dict[str, Any]:
    """Create a definition to run the given entrypoint on the given container.

    Arguments:
        taskdef:
            task definition to use in the container definition
        container_name:
            name of the container to use as a template for the new
            container definition
        entrypoint:
            new entryPoint for the container definition

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
        command=entrypoint,
        portMappings=[],  # nothing should connect to this container
    )
    return container_definition  # type: ignore


def _runtask(body: Dict[str, Union[str, None]]) -> Boto3Result:
    """Runs an ECS service optionally updating the task command.

    Arguments:
        body: A dictionary with the command body.

    Keys:
        taskdef_entrypoint: If set, the entryPoint command field in the ECS
        task definition will be changed to this value before the task is
        started.
    """
    try:
        taskdef_entrypoint = body["entrypoint"]
    except KeyError:
        taskdef_entrypoint = None

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

    if taskdef_entrypoint:
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
                        service_taskdef, _container_name, taskdef_entrypoint
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
    """Wait for a task to finish.

    Holds execution until the given task_arn on the given cluster is not
    running, or a timeout is exceeded.

    Arguments:
        ecs: A boto3.client object.
        cluster: A string with the name of the cluster where the task_arn can
            be found.
        task_arn: A string with the task_arn to wait for.
        delay: An int indicating how long to wait between attempts.
        attempts: An int indicating how many times to check if execution has
            finished before timing out.

    Returns:
        Boto3Result: If any exception was raised by the get_waiter call,
            including a timeout exception, the exc attribute will be set.
            Otherwise, the response attribute will be set.
    """
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


def _deploy(body: Dict[str, Union[str, List[str]]]) -> Boto3Result:
    """Deploy containers on an ECS service.

    Arguments:
        body: A dictionary with the following elements.

    Keys:
        cluster_id: Name or ARN of of the cluster that hosts the services to
        deploy.

        service_ids: A list of services to deploy the image into. Can be short
        names or ARNs.

        image: The fully qualified image:tag pair that will be deployed into
        each container definition in the service. If this is None, the services
        in service_ids will be restarted without changes to their container
        definitions.

    Returns:
        Boto3Result with a list of ARNs of services that were updated.

    Raises:
        KeyError: If any key is missing from the body.

        TypeError: If the service_ids value is not a list of strings, or any
        other value is not a string.
    """
    ecs_service = Dict[str, str]

    ecs: boto3.client = boto3.client("ecs")

    cluster_id: str = cast(str, body["cluster_id"])
    service_ids: List[str] = cast(List[str], body["service_ids"])
    image: str = cast(str, body["image"])

    r = invoke(
        ecs.describe_services,
        **{"cluster": cluster_id, "services": service_ids},
    )
    if r.exc:
        return r
    described_services: List[ecs_service] = r.body["services"]

    target_services: List[ecs_service] = [
        svc
        for svc in described_services
        if svc["serviceName"] in service_ids
        or svc["serviceArn"] in service_ids
    ]

    updated_services: List[str] = []
    for service in target_services:
        taskdef_arn = service["taskDefinition"]
        r = invoke(
            ecs.describe_task_definition, **{"taskDefinition": taskdef_arn}
        )
        if r.exc:
            return r
        taskdef = r.body["taskDefinition"]

        if not image:
            # redeploy the service with the same task definition
            new_taskdef_arn: str = taskdef["taskDefinitionArn"]
        else:
            # register a modified task definition with the new container
            # definitions
            service_containerdefs = taskdef["containerDefinitions"].copy()

            for containerdef in service_containerdefs:
                containerdef.update(image=image)

            taskdef.update(service_containerdefs)

            r = invoke(ecs.register_task_definition, **taskdef)
            if r.exc:
                return r

            new_taskdef_arn = r.body["taskDefinition"]["taskDefinitionArn"]
            log("Registered task definition", new_taskdef_arn)

        r = update_service(
            ecs_client=ecs,
            cluster_id=cluster_id,
            service_name=service["serviceName"],
            taskdef_id=new_taskdef_arn,
            force_new_deployment=True,
        )
        if r.exc:
            return r
        else:
            service_arn: str = r.body["service"]["serviceArn"]
            log("Updated service", service_arn)
            updated_services.append(service_arn)

    success = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "UpdatedServiceArns": updated_services,
    }
    return Boto3Result(response=success)


__DISPATCH__ = {"runtask": _runtask, "deploy": _deploy}


def lambda_handler(
    event: Dict[str, Any], context: Any = None
) -> Dict[str, Any]:
    """Define a Lambda function entry-point.

    Takes an dictionary event, processes it, and logs a response message.

    Args:
        event: A dictionary with a command and body to pass to the command
        handler.

        context: This is ignored.

    Raises:
        The function will attempt to return unhandled exceptions in the return
        value.

    Returns:
        A dict with the data to be returned to the invoker.
    """
    start_t = time.time()
    log(msg="event received", data=event, level="info")
    try:
        command = event["command"]
        body = event["body"]
    except KeyError:
        err = _missing_required_keys(["command", "body"], list(event))
        log(msg=err["msg"], data=err["data"])
        return {"msg": err["msg"], "data": err["data"]}

    response = {"request_payload": {"command": command, "body": body}}
    result = __DISPATCH__[command](body)  # type: ignore
    if result.exc:
        response.update(result.error)
    else:
        response.update(result.body)

    duration = "{} ms".format(round(1000 * (time.time() - start_t), 2))
    log(
        msg="response received",
        data={"response": response, "duration": duration},
        level="info",
    )
    return {
        "msg": "response received",
        "data": {"response": response, "duration": duration},
    }


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s %(message)s", level=LOGGER_LEVEL)
    started_by = os.environ["USER"]
    event = json.loads(sys.argv[1])

    lambda_handler(event)
