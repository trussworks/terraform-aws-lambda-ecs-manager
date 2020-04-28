"""Helper functions for interacting with ECS services via boto3."""
import traceback
import types
from typing import Any, Dict, Optional


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
    """Call a function and return the response as a Boto3Result.

    Arguments:
        boto3_function: A callable to be called. Typically this will be a
            function in the boto3 module.
        **kwargs: A dictionary of arguments to pass when calling the
            boto3_function.

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
