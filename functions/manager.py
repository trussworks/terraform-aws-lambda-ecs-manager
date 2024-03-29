"""Lambda function for managing ECS tasks and services."""
import copy
import json
import logging
import os
import re
import sys
import time
import traceback
import types
from datetime import datetime
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union, cast

import boto3

LOGGER = logging.getLogger()
LOGGER_LEVEL = logging.INFO
LOGGER.setLevel(LOGGER_LEVEL)
STDOUT_HANDLER = logging.StreamHandler(sys.stdout)
STDOUT_HANDLER.setLevel(LOGGER_LEVEL)
LOGGER.addHandler(STDOUT_HANDLER)


def log(msg: str = "", data: Any = None, level: str = "debug") -> None:
    """Log a structured message to the console."""
    j = json.dumps({"message": msg, "data": data}, default=str)
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
    if not isinstance(required_keys, list) and not isinstance(
        found_keys, list
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
        "level": "critical",
    }


class Boto3Error(Exception):
    """Generic Boto3Error exception."""

    pass


class Boto3InputError(Boto3Error, AttributeError):
    """AttributeError variant for Boto3Error."""

    pass


class Boto3Result:
    """Result from a boto3 module call.

    Arguments:
        response: A dict returned from the boto3 call.
        exc: An exception raised by the boto3 call.

    Attributes:
        status: HTTPStatusCode that was returned with the response, if any.
        body: A copy of the response argument, if any.
        exc: If the boto3 call raised an exception, it will be named here.
        error: A dict with a parse stack trace from exc.

    Raises:
        Boto3InputError: If neither argument was both passed and has the
            correct type.
    """

    def __init__(
        self,
        response: Optional[Dict[str, Any]] = None,
        exc: Optional[Exception] = None,
    ):
        """Instance constructor.

        If an exception is passed, provide a dictionary representation of the
        traceback. Otherwise, store the response as an instance property.

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

        self.response = response
        self.body: Dict[str, Any] = response or {}
        self.exc: Optional[Exception] = exc

    @property
    def status(self) -> Optional[str]:
        """Return the HTTPStatusCode from the response, if it can be found."""
        if self.response is not None:
            status_code = self.response.get("ResponseMetadata", {}).get(
                "HTTPStatusCode"
            )
            return str(status_code)
        else:
            return None

    @property
    def error(self) -> Dict[str, Any]:
        """Return the response stacktrace, if any."""
        if self.exc:
            tb = traceback.TracebackException.from_exception(
                self.exc, capture_locals=True
            )
            return {
                "title": type(self.exc).__name__,
                "message": str(self.exc),
                "traceback": [line.split("\n") for line in tb.format()],
            }
        elif (self.response or {}).get("failures"):
            return {
                "title": "Response included failures",
                "message": (self.response or {}).get("failures"),
                "traceback": None,
            }
        elif (
            self.status
            and str(self.status) != "None"
            and str(self.status) != str(HTTPStatus.OK.value)
        ):
            return {
                "title": f"HTTP status not OK: {self.status}",
                "message": {"response": self.response},
                "traceback": None,
            }
        else:
            return {}

    def __repr__(self) -> str:
        """Return a printable string representation of the object."""
        return repr(self.error) if self.error else repr(self.body)


def invoke(boto3_function: types.FunctionType, **kwargs: Any) -> Boto3Result:
    """Call a function and return the response as a Boto3Result.

    Arguments:
        boto3_function: A callable to be called. Typically this will be a
            function in the boto3 module.
        **kwargs: Arguments to pass when calling the boto3_function.

    Returns:
        Boto3Result: If any exception was raised by the boto3_function call,
            the exc attribute will be set. Otherwise, the response attribute
            will be set.
    """
    try:
        r = boto3_function(**kwargs)
    except Exception as exc:
        return Boto3Result(exc=exc)
    else:
        return Boto3Result(response=r or {})


def register_task_definition(
    ecs_client: boto3.client, taskdef: Dict[str, Any]
) -> Boto3Result:
    """Register a new task definition, iterating on an existing one.

    Arguments:
        ecs_client:
            A boto3 ecs client object to connect.
        taskdef:
            A dictionary representation of the task definition to be
            registered.

    Returns:
        Boto3Result
    """
    return invoke(
        ecs_client.register_task_definition,
        **{
            "family": taskdef["family"],
            "containerDefinitions": taskdef["containerDefinitions"],
            "executionRoleArn": taskdef["executionRoleArn"],
            "taskRoleArn": taskdef["taskRoleArn"],
            "networkMode": taskdef["networkMode"],
            "cpu": taskdef["cpu"],
            "memory": taskdef["memory"],
            "requiresCompatibilities": taskdef["requiresCompatibilities"],
        },
    )


def update_service(
    ecs_client: boto3.client,
    service_name: str,
    cluster_id: str,
    taskdef_id: Optional[str] = None,
    force_new_deployment: bool = False,
) -> Boto3Result:
    """Update an ECS service.

    Arguments:
        ecs_client: A boto3 ecs client object to connect.

        service_name: The name of the service to update. Required.

        cluster_id: The name or ARN of the cluster the service is running on.

        taskdef_id: The 'family:revision' or ARN of the task definition to run
        in the service being updated. If a revision is not specified, the
        latest ACTIVE revision is used.

        force_new_deployment: Performs a new deployment when there were no
        service definition changes. For example, the service can use a new
        Docker image with the same image/tag combination (imagename:latest) or
        to roll Fargate tasks onto a newer platform version.

    Returns:
        Boto3Result
    """
    new_service_definitions = {
        "cluster": cluster_id,
        "service": service_name,
        "taskDefinition": taskdef_id,
        "forceNewDeployment": force_new_deployment,
    }
    if taskdef_id:
        new_service_definitions["taskDefinition"] = taskdef_id

    return invoke(ecs_client.update_service, **new_service_definitions)


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
        msg = f"Definition for container {container_name} not found."
        log(msg=msg, data=container_definition, level="critical")
        raise KeyError(msg)

    container_definition["logConfiguration"]["options"][
        "awslogs-stream-prefix"
    ] = "lambda"
    container_definition.update(
        command=entrypoint,
        portMappings=[],  # nothing should connect to this container
    )
    return container_definition  # type: ignore


def _healthcheck(body: Dict[str, Union[str, None]]) -> Boto3Result:
    """Report the status of the tasks in a given task family.

    Pagination is not supported: up to 100 tasks will be returned.

    Arguments:
        body: A dictionary with the command body.

    Keys:
        cluster: The short name or full Amazon Resource Name (ARN) of the
        cluster that hosts the tasks to list. Required.

        family: The name of the family with which to filter the results.

        serviceName: The name of the service with which to filter the results.
        Specifying a service_name limits the results to tasks that belong to
        that service.

    Returns:
        Boto3Result with a status report on the given service(s), or an error.

    Raises:
        Boto3InputError: If cluster_id is not set or is not a string.
    """
    if not isinstance(body.get("cluster"), str):
        err_msg: Dict[str, str] = _missing_required_keys(
            ["cluster"], list(body)
        )
        log(**err_msg)
        return Boto3Result(exc=KeyError(err_msg))

    task_filters = {
        key: body.get(key)
        for key in ["cluster", "family", "serviceName"]
        if body.get(key)
    }

    ecs_client = boto3.client("ecs")

    # By default, list_tasks only returns RUNNING tasks. We have to call it
    # twice if we want STOPPED tasks also.
    task_filters.update(desiredStatus="RUNNING")
    r_running = invoke(ecs_client.list_tasks, **task_filters)
    if r_running.error:
        return r_running

    task_filters.update(desiredStatus="STOPPED")
    r_stopped = invoke(ecs_client.list_tasks, **task_filters)
    if r_stopped.error:
        return r_stopped

    # there is a race here: if a task has stopped after the first list_tasks
    # call finished, but before the second call finished, it may appear in the
    # results twice. Therefore, we de-duplicate the list of task ARNs
    task_arns: List[Optional[str]] = list(
        set(
            r_running.body.get("taskArns", [])
            + r_stopped.body.get("taskArns", [])
        )
    )

    if task_arns:
        r = invoke(
            ecs_client.describe_tasks,
            **{"cluster": body.get("cluster"), "tasks": task_arns},
        )
        if r.error:
            return r
    else:
        return Boto3Result(
            response={
                "msg": "No task ARNs were found with the given criteria.",
                "data": None,
            }
        )

    task_statuses: List[Dict[str, str]] = []
    for task in r.body["tasks"]:
        task_status = {
            key: task.get(key).isoformat()
            if isinstance(task.get(key), datetime)
            else task.get(key)
            for key in [
                "taskArn",
                "taskDefinitionArn",
                "connectivity",
                "healthStatus",
                "desiredStatus",
                "lastStatus",
                "startedAt",
                "stopCode",
                "stoppedReason",
                "executionStoppedAt",
                "failures",
            ]
        }

        container_statuses: List[Dict[str, str]] = []
        for container in task["containers"]:
            container_statuses.append(
                {
                    key: container.get(key)
                    for key in [
                        "containerArn",
                        "image",
                        "lastStatus",
                        "exitCode",
                        "reason",
                        "healthStatus",
                    ]
                }
            )

        task_status["containers"] = container_statuses

        task_statuses.append(task_status)

    return Boto3Result({"tasks": task_statuses})


def _runtask(body: Dict[str, Union[str, None]]) -> Boto3Result:
    """Runs an ECS service optionally updating the task command.

    Arguments:
        body: A dictionary with the command body.

    Keys:
        entrypoint: If set, the entryPoint command field in the ECS task
        definition will be changed to this value before the task is started.
        Optional.

        container_id: The container to run as a new task. If an 'entrypoint' is
        provided, then this is required.

        service_id: The service where the container can be found. Required.

        cluster_id: The cluster where the service can be found. Required.

    Returns:
        Boto3Result
    """
    taskdef_entrypoint: str = body.get("entrypoint") or ""
    if not isinstance(taskdef_entrypoint, str):
        err_msg = {
            "msg": "TypeError",
            "data": "'entrypoint' key must be of type string",
            "level": "critical",
        }
        log(**err_msg)
        return Boto3Result(exc=TypeError(err_msg))

    missing_required_keys: List[str] = []
    required_keys = {"service_id", "cluster_id"}
    validated = {
        key: value
        for key in required_keys
        for value in (body.get(key) or "",)
        if value and isinstance(value, str)
    }
    missing_required_keys = sorted(required_keys - validated.keys())

    if missing_required_keys:
        err_msg = _missing_required_keys(list(required_keys), list(body))
        log(**err_msg)
        return Boto3Result(exc=KeyError(err_msg))

    if "entrypoint" in body and "container_id" not in body:
        err_msg = {
            "msg": "container_id required to process entrypoint",
            "data": "when giving an entrypoint, container_id is required. "
            "found keys: {}".format(list(body)),
            "level": "critical",
        }
        log(**err_msg)
        return Boto3Result(exc=KeyError(err_msg))

    service_id = validated["service_id"]
    cluster_id = validated["cluster_id"]

    ecs = boto3.client("ecs")

    r = invoke(
        ecs.describe_services,
        **{"cluster": cluster_id, "services": [service_id]},
    )
    if r.error:
        return r
    netconf = r.body["services"][0]["networkConfiguration"]
    svc_taskdef_arn = r.body["services"][0]["taskDefinition"]

    if taskdef_entrypoint:
        container_id: str = body.get("container_id") or ""

        r = invoke(
            ecs.describe_task_definition, **{"taskDefinition": svc_taskdef_arn}
        )
        if r.error:
            return r
        service_taskdef = r.body["taskDefinition"]
        taskdef_family = service_taskdef["family"]

        # create and register a custom task definition by modifying the
        # existing service
        r = invoke(
            ecs.register_task_definition,
            **{
                "family": taskdef_family,
                "containerDefinitions": [
                    _generate_container_definition(
                        service_taskdef, container_id, taskdef_entrypoint
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
        if r.error:
            return r
        target_taskdef_arn = r.body["taskDefinition"]["taskDefinitionArn"]
        log(
            msg="Created task definition",
            data=target_taskdef_arn,
            level="info",
        )
    else:
        target_taskdef_arn = svc_taskdef_arn

    # run the task
    r = invoke(
        ecs.run_task,
        **{
            "cluster": cluster_id,
            "taskDefinition": target_taskdef_arn,
            "launchType": "FARGATE",
            "networkConfiguration": netconf,
            "startedBy": "lambda",
        },
    )
    if r.error:
        return r
    new_task_arn = r.body["tasks"][0]["taskArn"]
    log(msg="Running task", data=new_task_arn, level="info")

    # wait for the task to finish
    r = _task_wait(ecs=ecs, cluster=cluster_id, task_arn=new_task_arn)
    if r.error:
        return r
    log(
        msg="Finished waiting for task execution",
        data=new_task_arn,
        level="info",
    )

    # inspect task result
    r = invoke(
        ecs.describe_tasks, **{"cluster": cluster_id, "tasks": [new_task_arn]}
    )
    if r.error:
        return r

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

    success = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "taskArn": new_task_arn,
        "taskDefinitionArn": target_taskdef_arn,
        "taskStatus": task_status,
    }
    return Boto3Result(response=success)


def _task_wait(
    ecs: boto3.client,
    cluster: str,
    task_arn: str,
    delay: int = 15,
    attempts: int = 40,
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
    return r


def _map_ecs_ssm_parameters(
    ssm_client: boto3.client, stored_parameters: List[Dict[str, Any]]
) -> Boto3Result:
    """Map ECS parameters from a list of SSM Parameters.

    Read SSM tags for the given parameters and map those that have tag keyed
    `ENV_VAR_NAME`. Discard any Parameters that do not have such a tag.

    Arguments:
        ssm_client: A boto3.client("ssm") object.

        stored_parameters: A list of SSM Parameters.

    Returns:
        Boto3Result with a list of Paramater -> ENV_VAR_NAME pairings in
        dict format, suitable for conclusion in an ECS containerDefinition.
    """
    for parameter in stored_parameters:
        r = invoke(
            ssm_client.list_tags_for_resource,
            **{
                "ResourceType": "Parameter",
                "ResourceId": parameter.get("Name"),
            },
        )
        if r.error:
            return r
        else:
            parameter["Tags"] = r.body.get("TagList", [])
            tag_list = list(
                filter(
                    lambda tag: tag.get("Key") == "ENV_VAR_NAME",
                    parameter["Tags"],
                )
            )
            if len(tag_list) > 0:
                parameter["ENV_VAR_NAME"] = tag_list[0].get("Value")

    env_var_map: List[Optional[Dict[str, str]]] = [
        {
            "name": parameter.get("ENV_VAR_NAME", ""),
            "valueFrom": parameter.get("Name", ""),
        }
        for parameter in stored_parameters
        if parameter.get("ENV_VAR_NAME")
    ]

    return Boto3Result(response={"map": env_var_map})


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
        each container definition in each service. If this is None, the
        services in service_ids will be restarted without changes to their
        container definitions.

        secrets: A list of regular expressions to match against SSM Parameter
        names. Matching Parameters will be included in the task definition if,
        and only if, they also have an object tag with the key ENV_VAR_NAME.

    Returns:
        Boto3Result with a list of ARNs of services that were updated & the
        ARN of the task definition they were updated with, or an error.
    """
    ecs_service = Dict[str, str]

    ecs_client: boto3.client = boto3.client("ecs")

    cluster_id: str = cast(str, body.get("cluster_id"))
    service_ids: List[str] = cast(List[str], body.get("service_ids"))
    image: Optional[str] = cast(str, body.get("image"))
    secrets: Optional[List[str]] = cast(
        Optional[List[str]], body.get("secrets")
    )

    if cluster_id is None or service_ids is None:
        err_msg: Dict[str, str] = _missing_required_keys(
            ["cluster_id", "service_ids"], list(body)
        )
        log(**err_msg)
        return Boto3Result(exc=KeyError(err_msg))

    if secrets and not isinstance(secrets, list):
        return Boto3Result(exc=TypeError("secrets value must be of type list"))
    elif secrets and isinstance(secrets, list):
        try:
            engines = [re.compile(pattern) for pattern in secrets]
        except re.error as e:
            return Boto3Result(exc=e)

        ssm_client = boto3.client("ssm")
        paginator = ssm_client.get_paginator("describe_parameters")
        page_iterator = paginator.paginate()

        ssm_parameters: List[Dict[str, Any]] = []
        for page in page_iterator:
            ssm_parameters += [
                parameter
                for parameter in page.get("Parameters")
                if any(
                    engine.fullmatch(parameter.get("Name"))
                    for engine in engines
                )
            ]

        r = _map_ecs_ssm_parameters(ssm_client, ssm_parameters)
        if r.error:
            return r
        else:
            secrets_map: List[Dict[str, str]] = r.body["map"]

    r = invoke(
        ecs_client.describe_services,
        **{"cluster": cluster_id, "services": service_ids},
    )
    if r.error:
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
            ecs_client.describe_task_definition,
            **{"taskDefinition": taskdef_arn},
        )
        if r.error:
            return r
        taskdef = copy.deepcopy(r.body["taskDefinition"])

        # compute a modified task definition with the new container
        # definitions and secrets, if any
        for containerdef in taskdef["containerDefinitions"]:
            if secrets:
                containerdef.update(secrets=secrets_map)
            if image:
                containerdef.update(image=image)

        if taskdef != r.body["taskDefinition"]:
            log(
                msg="Re-deploying service with updated container definitions",
                data={
                    "taskdef": taskdef,
                    "service_containerdefs": taskdef["containerDefinitions"],
                    "executionRoleArn": taskdef["executionRoleArn"],
                },
                level="info",
            )

            r = register_task_definition(ecs_client, taskdef)
            if r.error:
                return r
            else:
                log(
                    msg="Registered task definition",
                    data=r.body["taskDefinition"]["taskDefinitionArn"],
                    level="info",
                )

        # if we registered a new task definition, 'r' is the response from the
        # register_task_definition call. otherwise, 'r' is the describe call
        new_taskdef_arn = r.body["taskDefinition"]["taskDefinitionArn"]

        r = update_service(
            ecs_client=ecs_client,
            cluster_id=cluster_id,
            service_name=service["serviceName"],
            taskdef_id=new_taskdef_arn,
            force_new_deployment=True,
        )
        if r.error:
            return r
        else:
            service_arn: str = r.body["service"]["serviceArn"]
            log(msg="Updated service", data=service_arn, level="info")
            updated_services.append(service_arn)

    success = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "UpdatedServiceArns": updated_services,
        "NewTaskdefArn": new_taskdef_arn,
    }
    return Boto3Result(response=success)


__DISPATCH__ = {
    "runtask": _runtask,
    "deploy": _deploy,
    "healthcheck": _healthcheck,
}


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
    err_msg: Dict[str, str]
    try:
        command = event["command"]
        body = event["body"]
    except KeyError:
        err_msg = _missing_required_keys(["command", "body"], list(event))
        log(**err_msg)
        return err_msg

    if command not in __DISPATCH__:
        err_msg = {
            "msg": f"Command not recognized: '{command}'.",
            "data": "Must be one of: {}".format(list(__DISPATCH__)),
            "level": "critical",
        }
        log(**err_msg)
        return err_msg
    else:
        result = __DISPATCH__[command](body)  # type: ignore
        response: Dict[str, Any] = {
            "request_payload": {"command": command, "body": body}
        }
        response.update(result.error or result.body)

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
