#!/usr/bin/env python3
#
"""boto3 response manager."""
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
    """Result from a boto3 module call."""

    def __init__(
        self,
        response: Optional[Dict[str, Any]] = None,
        exc: Optional[Exception] = None,
    ):
        """Instance constructor.

        If an exception is passed, provide a dictionary representation of the
        traceback. Otherwise, return the response object.
        """
        if not isinstance(response, dict) and not isinstance(exc, Exception):
            raise Boto3InputError("At least one argument is required")

        if response is not None:
            self.status = response.get("ResponseMetadata", {}).get(
                "HTTPStatusCode"
            )
        else:
            self.status = None

        self.body = response
        self.exc = exc
        self.error = self._get_error_msg()

    def _get_error_msg(self) -> Dict[str, Any]:
        """Return the response stacktrace, if any."""
        if self.exc is None:
            return {}

        tb = traceback.TracebackException.from_exception(self.exc)
        return {
            "title": type(self.exc).__name__,
            "message": str(self.exc),
            "traceback": list(tb.format()),
        }


def invoke(boto3_function: types.FunctionType, **kwargs: Any) -> Boto3Result:
    """Call a function and return the response as a Boto3Result."""
    pass
